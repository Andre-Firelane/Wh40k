import os
import time

import pygame

from game import config, sprites
from game.dice import REROLL_ANIMATION_DURATION, HIT_ROLL, SNAP_SHOT_HIT_ROLL, WOUND_ROLL, SAVE_ROLL
from game.ui import button_style
from game.ui.text_utils import wrap_text

# User supplied a die-face sprite (Sprites/Dice.png - a blank white/grey
# cube face, rounded corners, dark outline, no pips) to use instead of the
# plain drawn rounded rect. Path is relative to this file (not the CWD),
# two directories up to the repo root, so it resolves regardless of where
# the game is actually launched from.
DICE_SPRITE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Sprites", "Dice.png")

DICE_SIZE = 50
DICE_GAP = 12
GROUP_GAP = 30
DICE_TOP_MARGIN = 16
# User: "das würfel overlay darf nicht über die seiten panels gehen" - this
# whole panel is now confined to the `bounds_rect` draw() is given (the
# board area, excluding the left/right side panels) instead of the full
# window, so it can never sit on top of/hide a side-panel button again.
# MAX_PANEL_WIDTH additionally caps its own width within that area (User:
# "wir haben jetzt viel mehr platz in der breite... das panel sollte
# vielleicht nicht über die gesamte breite gehen") - on a wide board area it
# now reads as a comfortable, centered column instead of stretching
# edge-to-edge.
MAX_PANEL_WIDTH = 640
BACKDROP_MARGIN = 24  # horizontal inset from bounds_rect's own edges
CONTENT_PADDING = 16  # extra inset of text/dice from the panel/backdrop edge
BACKDROP_PADDING = 14  # vertical padding around the content, inside the backdrop
BACKDROP_COLOR = (15, 15, 18, 190)  # semi-transparent panel behind the roll, only while one is pending
BACKDROP_BORDER_COLOR = (90, 90, 90, 220)
DICE_BG_COLOR = (245, 245, 245)
SUCCESS_BG_COLOR = (150, 225, 150)
FAIL_BG_COLOR = (230, 130, 130)
DICE_BORDER_COLOR = (30, 30, 30)
DICE_VALUE_COLOR = (20, 20, 20)
# Standard western d6 pip layout, as (column, row) indices into a 3x3 grid
# spanning the die face - used instead of printing the digit as text.
PIP_LAYOUT = {
    1: [(1, 1)],
    2: [(0, 0), (2, 2)],
    3: [(0, 0), (1, 1), (2, 2)],
    4: [(0, 0), (2, 0), (0, 2), (2, 2)],
    5: [(0, 0), (2, 0), (0, 2), (2, 2), (1, 1)],
    6: [(0, 0), (2, 0), (0, 2), (2, 2), (0, 1), (2, 1)],
}
PIP_RADIUS_RATIO = 0.085  # fraction of the die's width
LABEL_COLOR = (255, 255, 255)
TARGET_COLOR = (255, 210, 90)
# The "who is shooting at whom" line above the roll's own heading. User:
# "wenn du beim wuerfel panel anzeigst, was auf wen schiesst, baue bitte die
# sprites mit ein, damit man es besser auf den ersten blick erkennen kann" -
# a name alone reads as text you have to parse ("2 Boyz 1 + Warboss"), the
# unit's own art is recognised at a glance. Attacker on the left in its own
# colour, target on the right in the existing TARGET_COLOR, an arrow between
# them, so which way the attack runs is readable without reading anything.
ATTACKER_COLOR = (150, 205, 255)
# The art sits in the same chamfered cell the Actions panel gives a unit
# listing (see its _draw_unit_portrait), so a unit reads the same wherever it
# is shown. User: "nutze fuer die sprites bitte auch diese kasten, die du auch
# bei der pregame anzeige nutzt in der linken spalte."
MATCHUP_PORTRAIT_PX = 54   # side of one (square) thumbnail cell
MATCHUP_PORTRAIT_INSET = 10  # art is fitted this much smaller than its cell
MATCHUP_PORTRAIT_BG = (8, 14, 22)
MATCHUP_PORTRAIT_CHAMFER = 6
MATCHUP_PORTRAIT_GAP = 4   # between two thumbnails of the same unit
MATCHUP_ART_TEXT_GAP = 8   # between a unit's art and its name
MATCHUP_SIDE_GAP = 12      # between a side and the word between them
# What sits between the two units. Was a drawn arrow; user: "ersetze den
# pfeil durch ein 'Attack' label. der pfeil ist ziemlich haesslich." Its
# width is measured, not declared - the font is whatever the OS gave us.
MATCHUP_VERB_TEXT = "ATTACK"
MATCHUP_VERB_COLOR = (225, 225, 225)
MATCHUP_BOTTOM_GAP = 8
# A side gives up thumbnails (second one first, then the last) rather than
# squeeze its name below this. Without it a narrow window turns a long
# attached-unit name into a one-character-per-line column: half the panel
# minus two portraits can be a couple of pixels wide, and wrap_text() only
# promises to fit what it is given.
MATCHUP_MIN_TEXT_PX = 90
# What a critical die BUYS, printed under the die itself. User: "markiere
# bitte die kritischen gewuerfelten treffer mit 'lethal hit', wenn diese
# Regel aktiv ist. Gleiches gilt fuer 'sustained hit' oder 'devastating
# wound'." The row's dice are spaced further apart while any such label is
# on screen - a label is wider than a 50px die, and crowding two of them
# into DICE_GAP would run them into each other.
# Drawn as a filled BADGE rather than as loose text. User: "außerdem hätte ich
# die Labels für crits bei lethal oder sustained gerne etwas auffälliger." Loose
# 11px gold on a dark panel is the quietest thing on screen, and it is marking
# the dice that matter most - the ones that bought an extra hit or skipped the
# wound roll entirely. A solid plate reads at a glance; the text sits DARK on
# it, which is the strongest contrast available here and the one the success
# dice already use (dark pips on a light face).
CRIT_LABEL_COLOR = (18, 14, 6)          # the text ON the badge
CRIT_LABEL_BG_COLOR = (255, 205, 70)    # the badge itself
CRIT_LABEL_BORDER_COLOR = (255, 240, 190)
CRIT_LABEL_PAD_X = 5
CRIT_LABEL_PAD_Y = 2
CRIT_LABEL_CHAMFER = 4
CRIT_LABEL_GAP = 5        # between the die and its badge
#: How wide a badge may get before its text wraps. Two dice wide: past that a
#: label starts dictating the whole row's spacing, and "DEVASTATING WOUND" on
#: two lines is tidier than a row half as long.
CRIT_LABEL_MAX_WIDTH = 2 * DICE_SIZE
#: Clear air between two neighbouring badges. The row's gap is DERIVED from the
#: badge that is actually rendered plus this, rather than being a constant that
#: has to be kept in step with the font by hand - the labels are as wide as the
#: words in them, and a fixed guess is how two badges came to sit 5px apart.
CRIT_LABEL_SEPARATION = 16
#: Rough vertical allowance for everything that is NOT dice - the matchup row,
#: the label bar, the result summary and the hint. Only used to decide whether
#: the panel has to grow WIDER (see _panel_width), never to place anything, so
#: an approximation is honest here: the real layout still measures itself.
#: Deliberately generous - guessing too small makes the panel widen a step
#: early, guessing too big lets it run off the bottom, and only one of those is
#: visible.
CHROME_HEIGHT_BUDGET = 200
HINT_COLOR = (230, 230, 230)
RESULT_SUMMARY_COLOR = (255, 150, 150)
REROLL_HIGHLIGHT_COLOR = (255, 210, 0)   # rule 15.02: border of a die currently being re-rolled
SELECTABLE_HIGHLIGHT_COLOR = (120, 200, 255)  # border shown on every die while picking one to re-roll
REROLL_FLICKER_INTERVAL = 0.06  # seconds between flickered faces while a re-roll animates

# User: "das würfel panel soll schnell von oben reinsliden, und nach der
# würfel strecke soll das panel wieder raussliden" - a slide-in/out on top
# of (not instead of) the existing pending/acknowledged mechanics, so the
# player always gets a moment to register that a new roll just appeared
# (and that the previous one just resolved) instead of it popping/vanishing
# instantly. Deliberately quick on the way in ("schnell") - it shouldn't
# feel like it's blocking anything - and a bit more relaxed on the way out,
# so the result stays legible for a beat before it's gone.
#
# User follow-up: "etwas schneller und etwas smoother, mit einer minimalen
# beschleunigung" - both durations trimmed a bit further, and the motion
# itself now runs through _ease_in() (see below) instead of linearly, so it
# visibly picks up speed rather than moving at a constant rate.
PANEL_SLIDE_IN_DURATION = 0.1
PANEL_SLIDE_OUT_DURATION = 0.18
# How much of _ease_in()'s curve is the quadratic (accelerating) term vs.
# plain linear - 0 would be pure linear, 1 pure "starts from a standstill"
# quadratic. Low on purpose: "minimal", not a dramatic ease.
SLIDE_ACCEL_BLEND = 0.35

# User follow-up: "während das panel noch slidet, soll die würfel animation
# abspielen bei den würfeln... und erst nach der animation erscheint der
# ergebnistext" - while the panel is sliding IN, every die flickers through
# random faces (like dice actually tumbling) instead of showing its real,
# already-known value - the success/fail coloring and result text (the Save
# Roll summary line, the "click to confirm" hint) only appear once it
# settles into SHOWN. A dedicated interval (not REROLL_FLICKER_INTERVAL,
# which is rule 15.02's separate single/few-die re-roll flicker) since the
# slide-in window is now quite short and still wants a few visible flickers
# in it.
ENTRANCE_FLICKER_INTERVAL = 0.045
# User follow-up: "die dice roll animation soll noch eine halbe sekunde
# länger gehen, nach dem slide" - the flicker no longer stops the instant the
# slide-in finishes; it keeps going for this much longer (panel already at
# rest, only the dice keep tumbling) before the result is revealed. This is
# the ROLLING phase between SLIDING_IN and SHOWN (see the phase constants
# below) - the flicker itself is one continuous animation across both
# SLIDING_IN and ROLLING (see _flicker_start), it just doesn't matter to the
# flicker whether the panel itself is still moving or already in place.
EXTRA_ROLL_DURATION = 0.5

# User color code for the dice panel's own heading (dice_manager.label, e.g.
# "Hit Roll: Bolter (3 attack(s))..."): a colored bar behind it, keyed off
# the roll's kind - Hit Roll orange, Wound Roll red, Save Rolls blue,
# everything else (advance/charge/damage/hazard/attacks/battle-shock, which
# has no kind at all) plain grey. SNAP_SHOT_HIT_ROLL is still a Hit Roll for
# this purpose (rule 15.09 only changes its re-roll eligibility, not what
# kind of roll it is).
LABEL_BAR_PADDING_X = 14
LABEL_BAR_PADDING_Y = 6
LABEL_BAR_GAP = 8
HIT_ROLL_BAR_COLOR = (120, 65, 8)
WOUND_ROLL_BAR_COLOR = (110, 18, 18)
SAVE_ROLL_BAR_COLOR = (12, 45, 92)
NORMAL_BAR_COLOR = (50, 50, 54)
_ROLL_KIND_BAR_COLORS = {
    HIT_ROLL: HIT_ROLL_BAR_COLOR,
    SNAP_SHOT_HIT_ROLL: HIT_ROLL_BAR_COLOR,
    WOUND_ROLL: WOUND_ROLL_BAR_COLOR,
    SAVE_ROLL: SAVE_ROLL_BAR_COLOR,
}

HIDDEN, SLIDING_IN, ROLLING, SHOWN, SLIDING_OUT = "hidden", "in", "rolling", "shown", "out"


def _ease_in(t):
    """A gentle "starts slow, picks up speed" curve for progress in [0, 1] -
    blends linear and quadratic by SLIDE_ACCEL_BLEND so the acceleration
    reads as present but subtle, not a hard snap."""
    return t * ((1.0 - SLIDE_ACCEL_BLEND) + SLIDE_ACCEL_BLEND * t)


def _panel_width(bounds_rect, dice_count, gap, row_height, height_budget):
    """How wide the panel should be for this many dice.

    MAX_PANEL_WIDTH stays the PREFERRED width, because it is a user decision -
    "das panel sollte vielleicht nicht über die gesamte breite gehen" - and on
    an ordinary roll nothing here changes it. It stops being a hard cap only
    when the dice would otherwise stack into more rows than there is room for:
    a 60-die roll ran 11px past the bottom of the board area at 640px, and
    growing sideways is the one way to spend fewer rows on the same dice.
    User: "die größe des würfelpanels muss sich anpassen."

    Widened in whole dice, not by pixels, since a fraction of a die buys
    nothing - and never past what the board area actually offers, which is the
    older decision this must not break ("das würfel overlay darf nicht über die
    seiten panels gehen")."""
    available = bounds_rect.width - 2 * BACKDROP_MARGIN
    preferred = min(available, MAX_PANEL_WIDTH)
    if dice_count <= 0 or row_height <= 0:
        return preferred
    width = preferred
    while width < available:
        rows = -(-dice_count // _max_per_row(width - 2 * CONTENT_PADDING, gap))
        if rows * row_height <= height_budget:
            break
        width = min(available, width + DICE_SIZE + gap)
    return width


def _max_per_row(text_max_width, gap):
    """How many dice fit on one row at `gap`, at least one.

    The +gap is the trailing gap the last die does not need: n dice measure
    n*DICE_SIZE + (n-1)*gap, so adding one gap to both sides of the division
    makes this exact rather than one-short."""
    return max(1, (text_max_width + gap) // (DICE_SIZE + gap))


class DicePanel:
    def __init__(self):
        self.target_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.label_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.value_font = pygame.font.SysFont(config.FONT_NAME, 28, bold=True)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        # Deliberately a notch smaller than target_font: the matchup line
        # holds two full unit names side by side in half the panel width
        # each, and an attached unit's name ("1 Crisis Starscythe Battlesuits
        # 1 + Commander in Coldstar Battlesuit") needs the extra characters
        # per line to not turn into five wrapped rows.
        self.matchup_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2, bold=True)
        # Small on purpose: a crit label sits under a single die, so its
        # widest word ("DEVASTATING") is what decides how far apart the dice
        # in a row have to be.
        self.crit_font = pygame.font.SysFont(config.FONT_NAME, 13, bold=True)
        self._die_rects = []  # [(original_index, rect), ...] from the last draw() - for click detection
        # The backdrop this panel actually put on screen last frame, or None
        # if it drew nothing (no roll, suppressed, finished sliding out).
        # Same lifetime as _die_rects above - a record of what was drawn,
        # not of what was asked for. main.py's AI badge reads it so the
        # badge can step out of a visible roll's way instead of landing on
        # top of it (rule 15.02's Command Re-roll fires while the roll is
        # still on screen - see main()'s show_thinking_overlay()).
        self.last_backdrop_rect = None

        # The die-face sprite, pre-scaled to DICE_SIZE once. Loaded
        # defensively - a missing/unreadable file just falls back to the
        # old plain drawn rounded rect (see _die_face_surface()) rather
        # than crashing the whole panel.
        self._dice_sprite = None
        try:
            sprite = pygame.image.load(DICE_SPRITE_PATH).convert_alpha()
            self._dice_sprite = pygame.transform.smoothscale(sprite, (DICE_SIZE, DICE_SIZE))
        except (pygame.error, FileNotFoundError):
            self._dice_sprite = None
        self._tinted_sprite_cache = {}  # bg color tuple -> tinted DICE_SIZE sprite Surface
        # Slide in/out state machine - deliberately decoupled from
        # dice_manager.is_pending itself: sliding OUT has to keep rendering
        # for a beat strictly AFTER the roll was already acknowledged (pending
        # cleared), which is exactly when is_pending goes False.
        self._phase = HIDDEN
        self._anim_start = None  # when the CURRENT phase began - used for that phase's own duration/offset
        self._flicker_start = None  # when the dice-flicker animation began - spans SLIDING_IN + ROLLING as one
        self._last_roll_id = None  # id() of the pending_values list currently on screen
        self._hold_start = None  # when the current suppressed (see draw()'s `suppressed`) stretch began
        self._last_draw_at = None  # time of the last NON-suppressed draw - where a hold picks up from

    @property
    def is_busy(self):
        """True whenever the panel is visually on screen in any way - fully
        shown, mid slide-in/out, or still rolling (see ROLLING) before the
        result reveals. Distinct from dice_manager.is_pending: the slide-OUT
        phase runs strictly after a roll (or a whole chained sequence of
        them, e.g. hit->wound->save) has already been acknowledged, so a
        caller that needs to know "is anything still visually happening
        with a roll right now" (main.py gates the AI's next action on this -
        see its own comment for the bug this fixes) must check this, not
        just is_pending."""
        return self._phase != HIDDEN

    def draw(self, surface, dice_manager, selecting_die=False, bounds_rect=None, suppressed=False):
        """`suppressed` withholds the panel entirely for this frame - used by
        main.py while a modal must-click-away overlay (a "Player 2 uses X"
        Stratagem notice, a WAAAGH! notice, the turn banner, the turn plan)
        is still unread. User report: the notice that the AI spent Explosives
        and that Stratagem's own 6D6 roll appeared in the SAME frame ("erst
        meldung, dann roll") - the roll is the notice's consequence, so it
        may not show up until the notice has been acknowledged. Those
        overlays already outrank a pending roll for input (main.py's event
        chain), so the dice couldn't be clicked away underneath one anyway.

        Time spent suppressed doesn't count against the animation: the phase
        clocks are shifted forward by however long the hold lasted, so a roll
        that started behind a notice still plays its full slide-in + tumble
        once the notice is gone (rather than jumping straight to its result,
        which is what simply skipping the draw call would do)."""
        self._die_rects = []
        self.last_backdrop_rect = None
        now = time.monotonic()
        if suppressed:
            if self._hold_start is None:
                # Held from the last frame that was actually rendered, not
                # from this one: the overlay went up somewhere between the
                # two, so that gap is part of the hold as well. Only matters
                # for correctness at the margins (one frame), but getting it
                # wrong is exactly the kind of small leak that makes a short
                # animation look like it "skipped".
                self._hold_start = self._last_draw_at if self._last_draw_at is not None else now
            return
        if self._hold_start is not None:
            held = now - self._hold_start
            self._hold_start = None
            if self._anim_start is not None:
                self._anim_start += held
            if self._flicker_start is not None:
                self._flicker_start += held
        self._last_draw_at = now
        pending = dice_manager.is_pending
        current_id = id(dice_manager.pending_values) if pending else None

        if pending:
            if self._phase in (HIDDEN, SLIDING_OUT) or current_id != self._last_roll_id:
                # A new roll just started - either from a dead stop, or
                # chained directly off the one before it within the very
                # same click's on_dice_acknowledged() (game/dice.py's roll()
                # always builds a brand new pending_values list, so an id()
                # change reliably means "this is a different roll", never
                # the in-place mutation a Command Re-roll does to the SAME
                # list via reroll_die()/reroll_all()).
                self._phase = SLIDING_IN
                self._anim_start = now
                self._flicker_start = now
            self._last_roll_id = current_id
        elif self._phase in (SLIDING_IN, ROLLING, SHOWN):
            # The roll (or the whole chain of them) just got acknowledged and
            # nothing further was queued behind it - slide back out instead
            # of just vanishing.
            self._phase = SLIDING_OUT
            self._anim_start = now
        elif self._phase == HIDDEN:
            return

        # `t` is the plain (linear) elapsed fraction of the CURRENT phase -
        # used for timing, i.e. deciding exactly when that phase is done.
        # `progress` is the eased version of that same fraction (see
        # _ease_in()) for SLIDING_IN/OUT - used only for the visual vertical
        # offset below, so the slide itself reads as accelerating rather
        # than moving at a constant rate.
        elapsed = now - self._anim_start if self._anim_start is not None else 0.0
        if self._phase == SLIDING_IN:
            t = min(1.0, elapsed / PANEL_SLIDE_IN_DURATION) if PANEL_SLIDE_IN_DURATION > 0 else 1.0
            progress = _ease_in(t)
            if t >= 1.0:
                # Panel has arrived - the dice keep rolling a bit longer
                # before the result is revealed (see EXTRA_ROLL_DURATION).
                self._phase = ROLLING
                self._anim_start = now
        elif self._phase == ROLLING:
            progress = 1.0  # already at rest - no more panel movement, only the dice keep flickering
            t = min(1.0, elapsed / EXTRA_ROLL_DURATION) if EXTRA_ROLL_DURATION > 0 else 1.0
            if t >= 1.0:
                self._phase = SHOWN
        elif self._phase == SLIDING_OUT:
            t = min(1.0, elapsed / PANEL_SLIDE_OUT_DURATION) if PANEL_SLIDE_OUT_DURATION > 0 else 1.0
            progress = 1.0 - _ease_in(t)
            if t >= 1.0:
                self._phase = HIDDEN
                self._last_roll_id = None
                self._flicker_start = None
                return
        else:
            progress = 1.0

        # Rule (user-supplied UX): the roll's outcome (die faces, success/
        # fail coloring, the result text) only "reveals" once the panel has
        # finished sliding in AND rolled a bit longer at rest - while it's
        # SLIDING_IN or ROLLING, the dice instead flicker through random
        # faces (see _draw_dice_row()) and the result text below is skipped
        # entirely, exactly mirroring how a real die still tumbling doesn't
        # show its result yet.
        revealed = self._phase == SHOWN
        # The flicker itself is one continuous animation spanning both
        # SLIDING_IN and ROLLING (see _flicker_start) - it doesn't restart
        # when the panel finishes moving and switches from one to the other.
        flicker_elapsed = now - self._flicker_start if self._flicker_start is not None else 0.0

        # DiceManager.acknowledge() only clears pending_values/rerolled_*
        # (see game/dice.py) - label/success_threshold/target_name/roll_kind/
        # damage_per_failure all live on, so the just-finished roll's
        # content is still available to keep rendering while it slides out.
        values = dice_manager.pending_values if pending else dice_manager.last_values
        if not values:
            return

        bounds_rect = bounds_rect if bounds_rect is not None else surface.get_rect()
        # The width has to be settled BEFORE the layout pass below, because
        # everything in it centres on the panel - so the dice-row height is
        # worked out here rather than read back afterwards. It is analytic:
        # one row is a die plus, while crit labels are up, their wrapped lines.
        row_gap = self._row_gap(dice_manager, revealed)
        crit_lines = self._crit_label_lines(dice_manager, revealed)
        row_height = DICE_SIZE + DICE_GAP
        if crit_lines:
            row_height += CRIT_LABEL_GAP + crit_lines * self.crit_font.get_height()
        # What is left for dice after the chrome above and below them. Measured
        # against the board area, which is the bound the panel already promises
        # never to leave.
        # ONE definition of where this panel starts, read by the height budget
        # here and by the layout below - they were two expressions saying the
        # same thing, and the moment they disagree the panel lays out for one
        # height and is measured against another.
        #
        # bounds_rect.y is now a real input rather than always 0: the round
        # progress bar owns the board's top strip and the caller hands over a
        # board rect that starts below it. PLAYER_BANNER_HEIGHT stays as a
        # FLOOR, because PlayerBanner draws its blocking warnings across the
        # full window width and this panel promised never to sit under them.
        top_y = max(bounds_rect.y, config.PLAYER_BANNER_HEIGHT) + DICE_TOP_MARGIN
        height_budget = (bounds_rect.bottom - top_y
                         - 2 * BACKDROP_PADDING - CHROME_HEIGHT_BUDGET)
        panel_width = _panel_width(bounds_rect, len(values), row_gap, row_height,
                                   height_budget)
        panel_left = bounds_rect.x + (bounds_rect.width - panel_width) // 2
        panel_centerx = panel_left + panel_width // 2

        threshold = dice_manager.success_threshold
        indexed = list(enumerate(values))
        if not revealed:
            # Still flickering - don't leak the outcome through dice
            # ordering/grouping either, keep the roll's own left-to-right
            # order instead of splitting into success/failure rows.
            dice_groups = (indexed,)
            failures = []
        elif threshold is not None:
            # DiceManager.is_success(), not a plain `>= threshold`: rules
            # 05.01/05.04 make an unmodified 1 fail no matter how far
            # modifiers pushed the threshold down - see that method's own
            # note for the user report this comes from.
            successes = sorted((i for i in indexed if dice_manager.is_success(i[1])), key=lambda pair: pair[1])
            failures = sorted((i for i in indexed if not dice_manager.is_success(i[1])), key=lambda pair: pair[1])
            dice_groups = (successes, failures)
        else:
            dice_groups = (sorted(indexed, key=lambda pair: pair[1]),)
            failures = []

        text_max_width = panel_width - 2 * CONTENT_PADDING
        y = top_y

        # The actual content (text/dice) is only drawn once the backdrop's
        # size is known, so every draw call is deferred into `ops` (a list
        # of no-arg closures) while this single layout pass also tracks the
        # final y - then the backdrop is drawn first (so it sits BEHIND
        # everything) and `ops` is replayed on top of it. `movable_rects`
        # collects every Rect created below (in absolute/"resting" screen
        # coordinates) so the slide-in/out offset can be applied to all of
        # them at once, in one place, after the offset itself is known -
        # each op's closure captures its Rect object by reference (a mutable
        # pygame.Rect), so shifting a rect here is reflected automatically
        # once that op actually runs.
        ops = []
        movable_rects = []

        target_squad = getattr(dice_manager, "target_squad", None)
        attacker_squad = getattr(dice_manager, "attacker_squad", None)
        if dice_manager.target_name or target_squad is not None:
            y = self._draw_matchup(
                ops, movable_rects, surface, attacker_squad, target_squad, dice_manager.target_name,
                y, text_max_width, panel_left, panel_width,
                subject_label=getattr(dice_manager, "subject_label", "Target") or "Target",
            )
            y += 4

        if dice_manager.label:
            y = self._draw_label_bar(
                ops, movable_rects, surface, dice_manager.label, self.label_font, dice_manager.roll_kind,
                y, text_max_width, panel_left, panel_width,
            )
            y += LABEL_BAR_GAP

        # THE GAP AND THE ROW LENGTH ARE ONE DECISION, and splitting them was a
        # reported bug: this counted dice per row at DICE_GAP while
        # _draw_dice_row() laid them out at the wider crit-label spacing
        # whenever a crit label was on screen. Ten dice then measured 734px
        # inside a 640px panel and hung 47px off EACH side - user: "die würfel
        # fliegen optisch aus dem würfelpanel wenn es zu viele werden."
        #
        # The gap is computed once, here, and handed down, so the count and the
        # layout cannot disagree again.
        max_per_row = _max_per_row(text_max_width, row_gap)
        entrance_elapsed = flicker_elapsed if not revealed else None
        for group in dice_groups:
            if not group:
                continue
            for row_start in range(0, len(group), max_per_row):
                y = self._draw_dice_row(
                    ops, movable_rects, surface, group[row_start:row_start + max_per_row], y,
                    dice_manager, selecting_die and pending and revealed, panel_left, panel_width,
                    entrance_elapsed=entrance_elapsed, gap=row_gap,
                )
                y += DICE_GAP
            y += GROUP_GAP - DICE_GAP  # extra breathing room between the success/failure blocks

        # Result text (the Save Roll summary, and the "click to confirm"
        # hint) is deliberately withheld until `revealed` - see this
        # method's own comment on `revealed` above for why.
        if revealed:
            # Extra feedback requested after a Save Roll: how many attacks
            # are about to get through, and for how much damage each -
            # computed straight from the roll (damage_per_failure is set
            # once, at roll time, from the melta-adjusted weapon - see
            # shooting.py/fight.py's _resolve_wounds()).
            if dice_manager.roll_kind == SAVE_ROLL and dice_manager.damage_per_failure is not None:
                failed_count = len(failures)
                if failed_count == 0:
                    summary = "All saves succeed - no damage gets through."
                else:
                    total_damage = failed_count * dice_manager.damage_per_failure
                    summary = (
                        f"{failed_count} attack(s) get through: {dice_manager.damage_per_failure} damage each "
                        f"({total_damage} total)."
                    )
                y = self._draw_wrapped(ops, movable_rects, surface, summary, self.label_font, RESULT_SUMMARY_COLOR, y, text_max_width, panel_centerx)
                y += 8

            hint = "Click a die to re-roll it." if (selecting_die and pending) else "Click to confirm"
            hint_surf = self.hint_font.render(hint, True, HINT_COLOR)
            hint_rect = hint_surf.get_rect(centerx=panel_centerx, y=y)
            movable_rects.append(hint_rect)
            ops.append(lambda s=hint_surf, r=hint_rect: surface.blit(s, r))
            y = hint_rect.bottom

        backdrop_rect = pygame.Rect(
            panel_left, top_y - BACKDROP_PADDING,
            panel_width, (y - top_y) + 2 * BACKDROP_PADDING,
        )

        # Slide the whole panel (backdrop + every rect drawn above) up above
        # bounds_rect's own top edge at progress==0, down to its normal
        # resting position at progress==1 - a single uniform vertical
        # translation, so nothing's relative layout changes, it just arrives
        # from/departs to off-screen-above.
        if progress < 1.0:
            hidden_travel = backdrop_rect.bottom - bounds_rect.top
            offset_y = round(-(1.0 - progress) * hidden_travel)
            if offset_y:
                backdrop_rect.move_ip(0, offset_y)
                for rect in movable_rects:
                    rect.move_ip(0, offset_y)

        self.last_backdrop_rect = backdrop_rect
        backdrop_surf = pygame.Surface(backdrop_rect.size, pygame.SRCALPHA)
        backdrop_surf.fill(BACKDROP_COLOR)
        pygame.draw.rect(backdrop_surf, BACKDROP_BORDER_COLOR, backdrop_surf.get_rect(), width=2, border_radius=8)
        surface.blit(backdrop_surf, backdrop_rect.topleft)

        for op in ops:
            op()

    def die_index_at(self, pos):
        for index, rect in self._die_rects:
            if rect.collidepoint(pos):
                return index
        return None

    def _draw_wrapped(self, ops, movable_rects, surface, text, font, color, y, max_width, centerx):
        for line in wrap_text(font, text, max_width):
            line_surf = font.render(line, True, color)
            line_rect = line_surf.get_rect(centerx=centerx, y=y)
            movable_rects.append(line_rect)
            ops.append(lambda s=line_surf, r=line_rect: surface.blit(s, r))
            y = line_rect.bottom + 2
        return y

    def _unit_side_size(self, squad, name, max_width):
        """(art surfaces, wrapped name lines, width, height) for one side of
        the matchup line, laid out as art-then-name within `max_width`.

        Measured before anything is drawn because the two sides have to agree
        on a common height (the arrow between them is centred on it) and
        because a side whose name is one line tall still has to reserve room
        for its thumbnail.

        Each thumbnail is a SQUARE cell (see MATCHUP_PORTRAIT_PX), so the cell
        is what is reserved rather than the art's own width - the art is
        centred in it, and the cell's chamfered frame is drawn at full size
        whether the figure inside is wide or narrow."""
        arts = [
            sprites.fitted_surface(path, MATCHUP_PORTRAIT_PX - MATCHUP_PORTRAIT_INSET)
            for path in (sprites.portrait_paths(squad, limit=2) if squad is not None else [])
        ]

        def art_width(items):
            if not items:
                return 0
            return (len(items) * MATCHUP_PORTRAIT_PX
                    + (len(items) - 1) * MATCHUP_PORTRAIT_GAP + MATCHUP_ART_TEXT_GAP)

        while arts and max_width - art_width(arts) < MATCHUP_MIN_TEXT_PX:
            arts.pop()
        art_w = art_width(arts)
        text_w = max(1, max_width - art_w)
        lines = wrap_text(self.matchup_font, name, text_w) if name else []
        line_h = self.matchup_font.get_height() + 1
        text_h = len(lines) * line_h
        width = art_w + (max(self.matchup_font.size(l)[0] for l in lines) if lines else 0)
        return arts, lines, width, max(text_h, MATCHUP_PORTRAIT_PX if arts else 0)

    def _draw_unit_side(self, ops, movable_rects, surface, arts, lines, color, x, y, height):
        """Draws one side of the matchup at (x, y), vertically centring both
        the art and the name block within `height` (the taller of the two
        sides) so a one-line name doesn't sit at the top of a three-line
        neighbour."""
        cursor = x
        for art in arts:
            cell = pygame.Rect(cursor, 0, MATCHUP_PORTRAIT_PX, MATCHUP_PORTRAIT_PX)
            cell.centery = y + height // 2
            movable_rects.append(cell)
            # `cell` is the same mutable Rect already in movable_rects, so the
            # art is centred off it LIVE, once the slide offset has been
            # applied - no second rect to keep in sync with it.
            ops.append(lambda a=art, r=cell: (
                button_style.draw_box(surface, r, chamfer=MATCHUP_PORTRAIT_CHAMFER,
                                      bg_color=MATCHUP_PORTRAIT_BG),
                surface.blit(a, a.get_rect(center=r.center)),
            ))
            cursor += MATCHUP_PORTRAIT_PX + MATCHUP_PORTRAIT_GAP
        if arts:
            cursor += MATCHUP_ART_TEXT_GAP - MATCHUP_PORTRAIT_GAP

        line_h = self.matchup_font.get_height() + 1
        text_y = y + (height - len(lines) * line_h) // 2
        for line in lines:
            line_surf = self.matchup_font.render(line, True, color)
            line_rect = line_surf.get_rect(x=cursor, y=text_y)
            movable_rects.append(line_rect)
            ops.append(lambda s=line_surf, r=line_rect: surface.blit(s, r))
            text_y += line_h

    def _draw_matchup(self, ops, movable_rects, surface, attacker_squad, target_squad, target_name,
                      y, max_width, panel_left, panel_width, subject_label="Target"):
        """The "who is attacking whom" line: attacker (art + name) on the
        left, an arrow, the target on the right - see ATTACKER_COLOR's own
        comment for the user report this comes from.

        Falls back to the old single centred "Target: X" line whenever there
        is no attacker to name (a battle-shock test, an Advance/Charge roll,
        a Damage roll resolved from inside DamageAllocationSession, which
        only knows who is being shot at). Art is optional throughout: a unit
        with no image of its own just renders as its name, the same "missing
        art is fine" convention sprite_for() has."""
        content_left = panel_left + CONTENT_PADDING
        centerx = panel_left + panel_width // 2
        target_name = target_name or (target_squad.name if target_squad is not None else "")

        if attacker_squad is None:
            arts, lines, width, height = self._unit_side_size(
                target_squad, f"{subject_label}: {target_name}", max_width,
            )
            self._draw_unit_side(
                ops, movable_rects, surface, arts, lines, TARGET_COLOR,
                centerx - width // 2, y, height,
            )
            return y + height + MATCHUP_BOTTOM_GAP

        verb_surf = self.matchup_font.render(MATCHUP_VERB_TEXT, True, MATCHUP_VERB_COLOR)
        half = max(1, (max_width - verb_surf.get_width() - 2 * MATCHUP_SIDE_GAP) // 2)
        a_arts, a_lines, _a_w, a_h = self._unit_side_size(attacker_squad, attacker_squad.name, half)
        t_arts, t_lines, _t_w, t_h = self._unit_side_size(target_squad, target_name, half)
        height = max(a_h, t_h)

        self._draw_unit_side(ops, movable_rects, surface, a_arts, a_lines, ATTACKER_COLOR,
                             content_left, y, height)
        self._draw_unit_side(ops, movable_rects, surface, t_arts, t_lines, TARGET_COLOR,
                             content_left + half + verb_surf.get_width() + 2 * MATCHUP_SIDE_GAP,
                             y, height)

        verb_rect = verb_surf.get_rect(center=(centerx, y + height // 2))
        movable_rects.append(verb_rect)
        ops.append(lambda s=verb_surf, r=verb_rect: surface.blit(s, r))
        return y + height + MATCHUP_BOTTOM_GAP

    def _draw_label_bar(self, ops, movable_rects, surface, text, font, roll_kind, y, max_width, panel_left, panel_width):
        """The dice panel's own heading (dice_manager.label) gets a colored
        bar behind it, per the user's color code - keyed off the roll's
        kind (see _ROLL_KIND_BAR_COLORS above). The bar spans the full
        panel width (like the Actions panel's own header bars), sized to
        fit however many lines the (possibly wrapped) label needs."""
        lines = wrap_text(font, text, max_width) or [text]
        line_height = font.get_height() + 2
        bar_height = len(lines) * line_height + 2 * LABEL_BAR_PADDING_Y
        bar_rect = pygame.Rect(panel_left, y, panel_width, bar_height)
        movable_rects.append(bar_rect)
        bar_color = _ROLL_KIND_BAR_COLORS.get(roll_kind, NORMAL_BAR_COLOR)
        ops.append(lambda r=bar_rect, c=bar_color: pygame.draw.rect(surface, c, r))

        text_y = y + LABEL_BAR_PADDING_Y
        centerx = panel_left + panel_width // 2
        for line in lines:
            line_surf = font.render(line, True, LABEL_COLOR)
            line_rect = line_surf.get_rect(centerx=centerx, y=text_y)
            movable_rects.append(line_rect)
            ops.append(lambda s=line_surf, r=line_rect: surface.blit(s, r))
            text_y += line_height

        return bar_rect.bottom

    def _draw_dice_row(
        self, ops, movable_rects, surface, row, y, dice_manager, selecting_die, panel_left, panel_width,
        entrance_elapsed=None, gap=None,
    ):
        """entrance_elapsed is only set while the roll hasn't `revealed` yet
        (SLIDING_IN or ROLLING - see draw()) - every die then flickers
        through random faces on a neutral background, its real value/
        success-or-failure withheld until it settles. `row`'s own values are
        still the TRUE ones throughout (only the on-screen digit/color is
        faked) - it's only ever grouped/ordered by draw() using the real
        values too, just never split into success/failure rows while not
        revealed, so no information leaks through layout either."""
        # A crit label is wider than the die it belongs to, so the whole row
        # spreads out while any is on screen (see _row_gap()). Only
        # while `revealed` - entrance_elapsed being set means the dice are
        # still tumbling, and the outcome, including which of them are
        # critical, must not leak through spacing either.
        crit_labels = tuple(getattr(dice_manager, "crit_labels", ()) or ())
        show_crits = bool(crit_labels) and entrance_elapsed is None
        # `gap` comes from draw(), which used the SAME number to decide how
        # many dice go in this row - see _row_gap(). Falling back to computing
        # it here keeps the method usable on its own, but the two must never be
        # derived independently again.
        if gap is None:
            gap = self._row_gap(dice_manager, entrance_elapsed is None)
        total_width = len(row) * DICE_SIZE + (len(row) - 1) * gap
        x = panel_left + (panel_width - total_width) // 2

        now = time.monotonic()
        entrance_tick = int(entrance_elapsed / ENTRANCE_FLICKER_INTERVAL) if entrance_elapsed is not None else None
        reroll_animating = (
            entrance_tick is None
            and dice_manager.rerolled_at is not None
            and now - dice_manager.rerolled_at < REROLL_ANIMATION_DURATION
        )

        placed = []  # (value, rect) for this row only - the crit labels below
        for index, value in row:
            die_rect = pygame.Rect(x, y, DICE_SIZE, DICE_SIZE)
            self._die_rects.append((index, die_rect))
            movable_rects.append(die_rect)
            placed.append((value, die_rect))
            x += DICE_SIZE + gap

            if entrance_tick is not None:
                # Rolling-dice flicker while still sliding in - staggered by
                # index (tick + index) so the dice don't all flash the same
                # face in lockstep, more like several dice actually tumbling.
                display_value = ((entrance_tick + index) % 6) + 1
                bg_color = DICE_BG_COLOR
                border_color, border_width = DICE_BORDER_COLOR, 2
            else:
                is_animating = reroll_animating and index in dice_manager.rerolled_indices
                display_value = value
                if is_animating:
                    tick = int((now - dice_manager.rerolled_at) / REROLL_FLICKER_INTERVAL)
                    display_value = (tick % 6) + 1

                # Same predicate the grouping above uses (and the same the
                # engine resolves with) - an unmodified 1 is red even when
                # modifiers took the threshold down to 1+.
                succeeded = dice_manager.is_success(value)
                if succeeded is None:
                    bg_color = DICE_BG_COLOR
                else:
                    bg_color = SUCCESS_BG_COLOR if succeeded else FAIL_BG_COLOR

                if is_animating:
                    border_color, border_width = REROLL_HIGHLIGHT_COLOR, 4
                elif selecting_die and index not in dice_manager.already_rerolled:
                    # A die that has already been re-rolled once cannot be
                    # picked (a dice can never be re-rolled more than once),
                    # so it deliberately does NOT get the selectable border -
                    # otherwise the panel would invite a click the engine
                    # then refuses.
                    border_color, border_width = SELECTABLE_HIGHLIGHT_COLOR, 3
                else:
                    border_color, border_width = DICE_BORDER_COLOR, 2

            # `rect` is the same (mutable) die_rect object already in
            # movable_rects, so it's already shifted for the slide-in/out
            # offset by the time this closure actually runs - no separate
            # "value rect" to keep in sync with it any more, pips are
            # positioned live off `rect` itself.
            def draw_die(rect=die_rect, bg=bg_color, bc=border_color, bw=border_width, value=display_value):
                self._draw_die_face(surface, rect, bg, bc, bw)
                self._draw_pips(surface, rect, value, DICE_VALUE_COLOR)

            ops.append(draw_die)
        if not show_crits:
            return y + DICE_SIZE

        # The labels themselves, under each critical die. Wrapped on whole
        # words at the die's own width - "DEVASTATING WOUND" is two lines,
        # "LETHAL HIT" fits on one at this size.
        label_lines = self._crit_label_texts(crit_labels)
        if not label_lines:
            return y + DICE_SIZE
        line_h = self.crit_font.get_height()
        rendered = [self.crit_font.render(line, True, CRIT_LABEL_COLOR) for line in label_lines]
        badge_w = max(s.get_width() for s in rendered) + 2 * CRIT_LABEL_PAD_X
        badge_h = len(rendered) * line_h + 2 * CRIT_LABEL_PAD_Y
        for value, rect in placed:
            if not dice_manager.is_critical(value):
                continue
            # ONE badge behind the whole label, not one per line: a two-line
            # label ("DEVASTATING WOUND") is one thing being said, and two
            # stacked plates would read as two.
            badge = pygame.Rect(0, 0, badge_w, badge_h)
            badge.centerx, badge.y = rect.centerx, rect.bottom + CRIT_LABEL_GAP
            movable_rects.append(badge)
            # The text rides the badge rect rather than carrying its own: the
            # slide-in offset is applied to every rect in movable_rects, and a
            # separately-tracked text rect would have to be shifted in step.
            ops.append(lambda b=badge, surfs=tuple(rendered): self._draw_crit_badge(surface, b, surfs))
        return y + DICE_SIZE + CRIT_LABEL_GAP + badge_h

    def _draw_crit_badge(self, surface, badge, line_surfs):
        """The filled plate plus its dark text - what makes a critical die
        readable at a glance instead of a caption under it."""
        points = button_style.chamfer_points(badge, CRIT_LABEL_CHAMFER)
        pygame.draw.polygon(surface, CRIT_LABEL_BG_COLOR, points)
        pygame.draw.lines(surface, CRIT_LABEL_BORDER_COLOR, True, points, 1)
        y = badge.y + CRIT_LABEL_PAD_Y
        for surf in line_surfs:
            surface.blit(surf, surf.get_rect(centerx=badge.centerx, y=y))
            y += surf.get_height()

    def _row_gap(self, dice_manager, revealed):
        """The horizontal gap between two dice in a row.

        ONE definition, because two things need the same number and used to
        work it out separately: draw() to decide how many dice fit on a row,
        and _draw_dice_row() to place them. Ten dice were then counted at
        DICE_GAP and laid out at the wider crit spacing, measuring 734px inside
        a 640px panel - user: "die würfel fliegen optisch aus dem würfelpanel".

        MEASURED off the badge that will actually be drawn, not a constant: a
        badge is as wide as the words in it, and the row has to hold it. Only
        once `revealed`, since which dice are critical must not leak through
        spacing while they are still tumbling."""
        crit_labels = tuple(getattr(dice_manager, "crit_labels", ()) or ())
        if not crit_labels or not revealed:
            return DICE_GAP
        width = self._crit_badge_width(crit_labels)
        return max(DICE_GAP, width - DICE_SIZE + CRIT_LABEL_SEPARATION)

    def _crit_badge_width(self, crit_labels):
        lines = self._crit_label_texts(crit_labels)
        if not lines:
            return 0
        return max(self.crit_font.size(line)[0] for line in lines) + 2 * CRIT_LABEL_PAD_X

    def _crit_label_texts(self, crit_labels):
        """The wrapped lines a crit label is drawn as.

        Wrapped narrower than the cell it sits in, so two labelled dice
        standing next to each other keep a visible gap between their text
        rather than reading as one run-on line.

        Its own method because draw() has to know how TALL a labelled row will
        be before it can choose the panel's width, and re-deriving that would
        be the same two-places-one-answer split that put the dice outside the
        panel in the first place."""
        lines = []
        for text in crit_labels:
            lines.extend(wrap_text(self.crit_font, text, CRIT_LABEL_MAX_WIDTH))
        return lines

    def _crit_label_lines(self, dice_manager, revealed):
        """How many label lines a row carries - 0 when none are shown."""
        if not revealed:
            return 0
        crit_labels = tuple(getattr(dice_manager, "crit_labels", ()) or ())
        return len(self._crit_label_texts(crit_labels))

    def _draw_die_face(self, surface, rect, bg_color, border_color, border_width):
        """User: use the Sprites/Dice.png sprite for the die face, tinted
        per its background color (neutral/success/fail - see
        _tinted_die_sprite()), instead of a plain drawn rounded rect. The
        sprite already has its own baked-in dark outline, so the extra
        highlight outline (gold re-roll flicker, light-blue selectable-die
        border - anything other than the plain default) is drawn as an
        overlay on top of it; falls back to the old flat rect+border look
        if the sprite failed to load."""
        sprite = self._tinted_die_sprite(bg_color)
        if sprite is not None:
            surface.blit(sprite, rect)
            if border_color != DICE_BORDER_COLOR or border_width != 2:
                pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=6)
        else:
            pygame.draw.rect(surface, bg_color, rect, border_radius=6)
            pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=6)

    def _tinted_die_sprite(self, color):
        """Multiplies the (near-white/grey/black) sprite by `color` -
        BLEND_RGBA_MULT scales each RGB channel by color/255 and leaves
        alpha untouched (color's own alpha is 255), so the sprite's shading/
        outline/rounded-corner transparency all come through unchanged,
        just recolored. Cached per color since draw() re-requests the same
        handful of colors every frame."""
        if self._dice_sprite is None:
            return None
        cached = self._tinted_sprite_cache.get(color)
        if cached is None:
            cached = self._dice_sprite.copy()
            cached.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._tinted_sprite_cache[color] = cached
        return cached

    def _draw_pips(self, surface, rect, value, color):
        """Standard d6 pips instead of a printed digit (see PIP_LAYOUT)."""
        positions = PIP_LAYOUT.get(value)
        if positions is None:
            # Defensive only - every roll in this game is a d6 (see
            # game/dice.py callers), so this shouldn't be reachable.
            value_surf = self.value_font.render(str(value), True, color)
            surface.blit(value_surf, value_surf.get_rect(center=rect.center))
            return
        xs = [rect.x + rect.width * f for f in (0.26, 0.5, 0.74)]
        ys = [rect.y + rect.height * f for f in (0.26, 0.5, 0.74)]
        radius = max(2, round(rect.width * PIP_RADIUS_RATIO))
        for col, row in positions:
            pygame.draw.circle(surface, color, (round(xs[col]), round(ys[row])), radius)
