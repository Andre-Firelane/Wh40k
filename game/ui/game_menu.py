"""The game's own menu: start a battle, resume one, save one, leave.

WHY THIS EXISTS. Until now the application had no frame around it. main() fell
straight into the map picker, and the only way out was ESC in fullscreen -
which ended the PROCESS. There was no way to leave a battle without leaving the
game, no way to begin a second one without restarting, and no way to reopen a
saved position except `python main.py --load <file>` from a shell.

TWO HOSTS, ONE DEFINITION. The same menu is shown in two places:

  * at STARTUP, as a full screen of its own, driven by tile_screen.run_screen()
    exactly like the map and army pickers;
  * IN A BATTLE, as an overlay over the frozen board, opened by ESC or by the
    little MENU button in the board's top-right corner.

Two copies of a menu would be two menus a week later (CLAUDE.md error class
10), so everything is shared - the panel rectangle, the stacked entry rects,
the hit-testing, the keyboard handling, the painting - and exactly TWO things
branch on `in_game`:

  1. the BACKDROP: a scrim over the live frame, or a filled screen with the
     same header the other two pre-battle screens use;
  2. the ENTRIES: a battle in progress can be resumed and saved; at startup
     "resume" means a file on disk instead, and there is nothing to save.

RESUME MEANS TWO THINGS, AND THAT IS THE POINT (user, asked directly: "Beides,
je nach Ort"). In a battle it is the way back to the board - the same answer
ESC gives. At startup it is the newest snapshot in scenes/. Both are "carry on
with the game you were playing"; they differ only in whether that game is still
in memory.

ONE CLICK, ONE ACTION - deliberately NOT the two-beat select-then-confirm the
map and army pickers use. That rule was introduced there because a stray click
decided the battlefield; here the user was offered a confirmation step for the
destructive entry and turned it down. The named consequence: a misclick on
"Start New Game" during a battle abandons it. The autosave is what makes that
survivable, which is why the two were asked for together.

run() NEVER RETURNS None, which is a deliberate difference from
MapSelectScreen.run() and ArmySelectScreen.run(). Those return None for
"abandoned", because they have no quit button and closing the window is the
only way to say no. This screen HAS a Quit entry, so ESC and the window's close
box answer QUIT rather than inventing a fourth meaning for the same gesture.
"""

import pygame

from game import config, sprites
from game.ui import button_style, tile_screen as ts

# The whole return contract. run() answers with one of these, and the in-game
# host hands one of these back to main() - so there is one vocabulary rather
# than a screen's and an overlay's.
NEW_GAME = "new_game"
RESUME = "resume"
SAVE = "save"
QUIT = "quit"

TITLE = "WARHAMMER 40,000"

# Grew with tile_screen's fonts (user: "Die Font im Main Menu und Auswahl
# screen darf viel groesser sein"): the entries are drawn with fonts["label"],
# the heading with fonts["name"] and the notes with fonts["small"], and a 460px
# panel was measured against the old, smaller set.
#
# PANEL_WIDTH is the load-bearing one - a note is rendered as ONE unwrapped,
# centred line, so a panel narrower than its longest note ("abandon this battle
# and pick a new map and armies", 370px at the new size) draws it straight over
# its own border. ENTRY_HEIGHT is SPACING and nothing more: draw_button() grows
# a row that is too short for its label all by itself, so the old 46 would still
# have worked - its own A/B probe said so. It follows the type because a 19px
# label in a 46px row reads as a taller font in the same old box.
#
# Everything else here is already derived from font heights (panel_rect,
# layout), and test_menu_presentation.py checks all of it at 1280x720.
PANEL_WIDTH = 560
PANEL_PAD = 26
ENTRY_HEIGHT = 58
ENTRY_GAP = 12
NOTE_GAP = 3
HEADING_GAP = 18

SCRIM_COLOR = (0, 0, 0, 185)
# The startup host's backdrop art, and the veil over it (user:
# "main-manu-background.jpg als hintergrund im hauptmenue setzen"). The veil is
# not decoration: this screen puts gold heading text, a bordered panel and a
# right-aligned key hint straight on top of a photograph, and without it their
# contrast depends on whatever happens to be behind them. 150 is measured -
# dark enough that the panel and the header bar keep the separation they had
# against the flat fill, light enough that the picture is still a picture.
#
# The IN-BATTLE host is deliberately untouched: its backdrop is the frozen
# board, which is the whole point of a pause screen.
BACKGROUND_VEIL_COLOR = (0, 0, 0, 150)
PANEL_BORDER_COLOR = (200, 165, 70)
HEADING_COLOR = (255, 215, 0)
NOTE_COLOR = (150, 170, 190)
DISABLED_NOTE_COLOR = (110, 118, 128)

# The board-corner opener. MARGIN matches game/ui/ai_busy_badge.py's, because
# these two controls share that corner and a second margin constant would be
# two answers to "how far in do things sit up there".
BUTTON_MARGIN = 12
BUTTON_WIDTH = 74
BUTTON_HEIGHT = 26


def _entry_label(action, in_game):
    if action == NEW_GAME:
        return "Start New Game"
    if action == RESUME:
        return "Resume Game"
    if action == SAVE:
        return "Save Game"
    return "Quit Game"


class GameMenu:
    """The menu, in whichever of its two homes.

    `in_game` picks the host. `save_path`/`save_note` are the startup host's
    Resume entry: a path to offer, and one line describing it. Both None means
    there is nothing to resume, and the entry is drawn greyed rather than
    dropped - see entries()."""

    def __init__(self, in_game=False, save_path=None, save_note=None):
        self.in_game = in_game
        self.save_path = save_path
        self.save_note = save_note
        self.action = None
        self.hovered = None
        self.keyboard_index = 0
        self._rects = []       # [(action, Rect, enabled)], set by layout()
        self._open = False
        self.fonts = ts.make_fonts()

    # -- what is on offer ---------------------------------------------------
    def entries(self):
        """(action, label, enabled, note) per row, in the order they are shown.

        The ONE place the two hosts differ in content. In a battle the first
        entry is Resume, because that is what ESC means and what most presses
        want; at startup the first is Start New Game, which is the order the
        user asked for ("start new game, resume game und quit game").

        A disabled Resume STAYS on screen, greyed. That is the opposite of
        tile_screen's "no chrome for a control that cannot do anything" rule,
        and deliberately: dropping it would silently change the menu's shape
        between the two hosts, and the reason it cannot be pressed - that no
        save exists yet - is the useful thing to show."""
        if self.in_game:
            return [
                (RESUME, _entry_label(RESUME, True), True, "back to the battle"),
                (SAVE, _entry_label(SAVE, True), True, "write a snapshot you can come back to"),
                (NEW_GAME, _entry_label(NEW_GAME, True), True,
                 "abandon this battle and pick a new map and armies"),
                (QUIT, _entry_label(QUIT, True), True, "leave the game"),
            ]
        # BOTH halves, not just the path. summary() answers None for a file
        # that cannot be read at all - corrupt, or from a newer format - and
        # that None is the eligibility gate (CLAUDE.md error class 5): without
        # it the entry would be offered and the press would then fail, which
        # is the one thing an "engine must not offer what it will not accept"
        # rule exists to stop.
        resumable = self.save_path is not None and self.save_note is not None
        return [
            (NEW_GAME, _entry_label(NEW_GAME, False), True, "pick a battlefield and two armies"),
            (RESUME, _entry_label(RESUME, False), resumable,
             self.save_note if resumable else "no saved game yet"),
            (QUIT, _entry_label(QUIT, False), True, "leave the game"),
        ]

    # -- the picker protocol tile_screen.run_screen() needs -----------------
    @property
    def done(self):
        return self.action is not None

    @property
    def cancelled(self):
        """Never. ESC answers QUIT here rather than abandoning the screen -
        this menu has a Quit entry, so there is nothing for a separate
        "cancelled" state to mean."""
        return False

    # -- the in-game half ---------------------------------------------------
    @property
    def is_pending(self):
        return self._open

    def show(self):
        self.action = None
        self.hovered = None
        self.keyboard_index = 0
        self._open = True

    def dismiss(self):
        self._open = False
        self.action = None

    def take_action(self):
        """The answer, once, then forgotten.

        Polled by main() after its event loop, the same idiom as
        UnshroudedTruthController.take_pending_placement() - an overlay cannot
        write main()'s locals, and clearing it here rather than at the call
        site is what stops one press being read twice."""
        action, self.action = self.action, None
        return action

    # -- geometry: ONE definition, read by draw() AND by hit-testing --------
    def panel_rect(self, screen_rect):
        rows = len(self.entries())
        height = (PANEL_PAD * 2
                  + self.fonts["name"].get_height() + HEADING_GAP
                  + rows * ENTRY_HEIGHT + (rows - 1) * ENTRY_GAP
                  + rows * (self.fonts["small"].get_height() + NOTE_GAP))
        rect = pygame.Rect(0, 0, PANEL_WIDTH, height)
        rect.center = screen_rect.center
        return rect

    def layout(self, screen_rect):
        """The entry rectangles, top to bottom. Called by draw() and again by
        handle_event() before any hit test - computing the same rectangle in
        two places is how a control ends up a few pixels off the thing it looks
        like it is in (the lesson tile_screen.header_bar() exists for)."""
        panel = self.panel_rect(screen_rect)
        y = panel.y + PANEL_PAD + self.fonts["name"].get_height() + HEADING_GAP
        note_height = self.fonts["small"].get_height() + NOTE_GAP
        self._rects = []
        for action, _label, enabled, _note in self.entries():
            rect = pygame.Rect(panel.x + PANEL_PAD, y,
                               panel.width - 2 * PANEL_PAD, ENTRY_HEIGHT)
            self._rects.append((action, rect, enabled))
            y += ENTRY_HEIGHT + note_height + ENTRY_GAP
        return self._rects

    def entry_at(self, pos):
        """The action under `pos`, or None. A DISABLED entry answers None -
        it swallows its own click rather than letting it fall through to
        whatever is behind the menu."""
        for action, rect, enabled in self._rects:
            if rect.collidepoint(pos):
                return action if enabled else None
        return None

    def _enabled_actions(self):
        return [action for action, _rect, enabled in self._rects if enabled]

    # -- input --------------------------------------------------------------
    def handle_event(self, event, screen_rect):
        """True while the menu is still up. Consumes everything it is given -
        both hosts hand it every event while it is open."""
        if event.type == pygame.QUIT:
            self.action = QUIT
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            # In a battle ESC is the way BACK, matching the key that opened
            # the menu. At startup there is no battle to go back to, so the
            # same key answers the entry that leaves.
            self.action = RESUME if self.in_game else QUIT
            return False
        self.layout(screen_rect)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN):
            actions = self._enabled_actions()
            if actions:
                step = -1 if event.key == pygame.K_UP else 1
                self.keyboard_index = (self.keyboard_index + step) % len(actions)
                self.hovered = actions[self.keyboard_index]
            return True
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            actions = self._enabled_actions()
            if actions:
                self.action = actions[min(self.keyboard_index, len(actions) - 1)]
            return not self.done
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.entry_at(event.pos)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self.entry_at(event.pos)
            if action is not None:
                self.action = action
            return not self.done
        return True

    # -- painting -----------------------------------------------------------
    def draw(self, surface, mouse_pos=None):
        screen_rect = surface.get_rect()
        if self.in_game:
            scrim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            scrim.fill(SCRIM_COLOR)
            surface.blit(scrim, (0, 0))
        else:
            self._draw_backdrop(surface, screen_rect)
            ts.draw_header(surface, screen_rect, self.fonts, TITLE,
                           "Choose how to begin.", PANEL_BORDER_COLOR)
            # page_count 1 and no confirm label means this draws nothing but
            # the right-aligned key hint - and "ESC quits" is literally true
            # on this host, which is why it can be reused verbatim.
            ts.draw_footer(surface, screen_rect, self.fonts, 0, 1)

        panel = self.panel_rect(screen_rect)
        button_style.draw_box(surface, panel, border_color=PANEL_BORDER_COLOR,
                              bg_color=button_style.BOX_BG_COLOR, border_width=2)
        heading = "PAUSED" if self.in_game else "MAIN MENU"
        surf = self.fonts["name"].render(heading, True, HEADING_COLOR)
        surface.blit(surf, surf.get_rect(centerx=panel.centerx, y=panel.y + PANEL_PAD))

        self.layout(screen_rect)
        mouse = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
        note_font = self.fonts["small"]
        for (action, rect, enabled), (_a, label, _e, note) in zip(self._rects, self.entries()):
            if enabled:
                button_style.draw_button(
                    surface, rect, label, self.fonts["label"],
                    hovered=rect.collidepoint(mouse) or self.hovered == action,
                    accent=self._accent(action),
                )
            else:
                # The toggle-off palette already means "not a live control" in
                # this HUD, so a second grey is not invented for it.
                button_style.draw_box(surface, rect, bg_color=button_style.TOGGLE_BG_OFF,
                                      border_color=button_style.TOGGLE_BORDER_OFF,
                                      border_width=1)
                text = self.fonts["label"].render(label.upper(), True,
                                                  button_style.TOGGLE_TEXT_OFF)
                surface.blit(text, text.get_rect(center=rect.center))
            if note:
                colour = NOTE_COLOR if enabled else DISABLED_NOTE_COLOR
                note_surf = note_font.render(note, True, colour)
                surface.blit(note_surf, note_surf.get_rect(centerx=rect.centerx,
                                                           y=rect.bottom + NOTE_GAP))

    def _draw_backdrop(self, surface, screen_rect):
        """The startup host's background: the supplied artwork under a dark
        veil, or the flat fill it used before if the file is not there.

        Missing art costs a picture, never the screen - the same convention
        every other lookup in game/sprites.py follows, and the reason the menu
        is still usable on a checkout without the Sprites folder."""
        path = sprites.menu_background_path()
        if path is None:
            surface.fill(ts.BG_COLOR)
            return
        try:
            surface.blit(sprites.menu_background_surface(path, screen_rect.size),
                         screen_rect.topleft)
        except pygame.error:
            surface.fill(ts.BG_COLOR)
            return
        veil = pygame.Surface(screen_rect.size, pygame.SRCALPHA)
        veil.fill(BACKGROUND_VEIL_COLOR)
        surface.blit(veil, screen_rect.topleft)

    def _accent(self, action):
        """What a press COSTS, which is what an accent means in this HUD (see
        game/ui/button_style.py): blue free, green carry on, red gives
        something up. Start New Game is therefore blue at startup and RED in a
        battle - there it costs the battle."""
        if action == RESUME:
            return "confirm"
        if action == QUIT:
            return "danger"
        if action == NEW_GAME and self.in_game:
            return "danger"
        return None

    def run(self, screen, clock=None):
        """The startup host. Always answers with one of the three actions."""
        ts.run_screen(screen, self, clock)
        return self.action or QUIT

    # -- the little opener on the board -------------------------------------
    def button_rect(self, board_rect):
        """The MENU button, in the board's top-right corner - "links oben neben
        dem rechten panel". Fixed rather than dodging anything: a button that
        moves is worse than a tight margin, and this one in particular has to
        be in the same place every time.

        Measured clear of the dice panel at both ends of the window sizes this
        game is run at - see test_game_menu.py, which pins the arithmetic."""
        return pygame.Rect(board_rect.right - BUTTON_MARGIN - BUTTON_WIDTH,
                           board_rect.y + BUTTON_MARGIN,
                           BUTTON_WIDTH, BUTTON_HEIGHT)

    def draw_button(self, surface, board_rect, mouse_pos=None):
        rect = self.button_rect(board_rect)
        mouse = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
        button_style.draw_button(surface, rect, "Menu", self.fonts["small"],
                                 hovered=rect.collidepoint(mouse))
        return rect
