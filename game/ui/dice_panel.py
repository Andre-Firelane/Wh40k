import os
import time

import pygame

from game import config
from game.dice import REROLL_ANIMATION_DURATION, HIT_ROLL, SNAP_SHOT_HIT_ROLL, WOUND_ROLL, SAVE_ROLL
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


class DicePanel:
    def __init__(self):
        self.target_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.label_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.value_font = pygame.font.SysFont(config.FONT_NAME, 28, bold=True)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self._die_rects = []  # [(original_index, rect), ...] from the last draw() - for click detection

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
        panel_width = min(bounds_rect.width - 2 * BACKDROP_MARGIN, MAX_PANEL_WIDTH)
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
        top_y = config.PLAYER_BANNER_HEIGHT + DICE_TOP_MARGIN
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

        if dice_manager.target_name:
            y = self._draw_wrapped(
                ops, movable_rects, surface, f"Target: {dice_manager.target_name}", self.target_font, TARGET_COLOR,
                y, text_max_width, panel_centerx,
            )
            y += 4

        if dice_manager.label:
            y = self._draw_label_bar(
                ops, movable_rects, surface, dice_manager.label, self.label_font, dice_manager.roll_kind,
                y, text_max_width, panel_left, panel_width,
            )
            y += LABEL_BAR_GAP

        max_per_row = max(1, (text_max_width + DICE_GAP) // (DICE_SIZE + DICE_GAP))
        entrance_elapsed = flicker_elapsed if not revealed else None
        for group in dice_groups:
            if not group:
                continue
            for row_start in range(0, len(group), max_per_row):
                y = self._draw_dice_row(
                    ops, movable_rects, surface, group[row_start:row_start + max_per_row], y,
                    dice_manager, selecting_die and pending and revealed, panel_left, panel_width,
                    entrance_elapsed=entrance_elapsed,
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
        entrance_elapsed=None,
    ):
        """entrance_elapsed is only set while the roll hasn't `revealed` yet
        (SLIDING_IN or ROLLING - see draw()) - every die then flickers
        through random faces on a neutral background, its real value/
        success-or-failure withheld until it settles. `row`'s own values are
        still the TRUE ones throughout (only the on-screen digit/color is
        faked) - it's only ever grouped/ordered by draw() using the real
        values too, just never split into success/failure rows while not
        revealed, so no information leaks through layout either."""
        total_width = len(row) * DICE_SIZE + (len(row) - 1) * DICE_GAP
        x = panel_left + (panel_width - total_width) // 2

        now = time.monotonic()
        entrance_tick = int(entrance_elapsed / ENTRANCE_FLICKER_INTERVAL) if entrance_elapsed is not None else None
        reroll_animating = (
            entrance_tick is None
            and dice_manager.rerolled_at is not None
            and now - dice_manager.rerolled_at < REROLL_ANIMATION_DURATION
        )

        for index, value in row:
            die_rect = pygame.Rect(x, y, DICE_SIZE, DICE_SIZE)
            self._die_rects.append((index, die_rect))
            movable_rects.append(die_rect)
            x += DICE_SIZE + DICE_GAP

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
        return y + DICE_SIZE

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
