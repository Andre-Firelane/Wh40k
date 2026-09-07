import pygame

from game import attached_units, config, enhancements, rules_text, starflare_ignition
from game.fight import effective_weapon_skill
from game.shooting import effective_ballistic_skill
from game.ui.text_utils import draw_wrapped_text, wrap_text, wrapped_text_height
from game.dice_notation import describe as describe_dice_notation
from game.weapons import MELEE, printed_keywords

BOX_BG_COLOR = (25, 25, 25)
BOX_BORDER_COLOR = (255, 215, 0)
NAME_COLOR = (255, 215, 0)
TEXT_COLOR = (230, 230, 230)
HEADER_COLOR = config.PANEL_HEADER_COLOR
TABLE_LINE_COLOR = (90, 90, 90)
# Weapon keywords sit under their row's numbers rather than in a column of
# their own, so they have to read as a caption and not as another value:
# same family as the gold headers, dimmer than the numbers above them.
KEYWORD_COLOR = (196, 170, 110)

ABILITY_TITLE_COLOR = (255, 205, 120)
ABILITY_LABEL_COLOR = (150, 195, 225)
SCROLLBAR_COLOR = (120, 120, 120)
SCROLLBAR_TRACK_COLOR = (55, 55, 55)
HINT_COLOR = (150, 150, 150)

BOX_WIDTH = 460
PADDING = 14
ROW_HEIGHT = 24
SECTION_GAP = 10
NAME_COLUMN_WIDTH = 140

ABILITY_GAP = 7           # between two printed abilities
BULLET_INDENT = 12

MOUSE_OFFSET = 24
SCREEN_MARGIN = 8         # the card never touches the window edge
MIN_CARD_HEIGHT = 120     # floor, so a tiny window still gets a scrollable card
SCROLL_STEP = 44          # pixels per wheel notch
SCROLLBAR_WIDTH = 5

# Hover-to-open. User: "zum einen haette ich das overlay gerne wenn man ein
# paar Sekunden ueber die Einheit hovert und nichts klickt."
HOVER_DELAY_MS = 900
HOVER_JITTER_PX = 6       # cursor drift this small still counts as resting


def printed_characteristic(weapon, which):
    """How a weapon's Attacks/Strength/Damage is PRINTED on its datasheet.

    Three of a weapon's characteristics can be a die roll rather than a fixed
    number (game/dice_notation.py: `attacks_notation`, `strength_notation`,
    `damage_notation`). Where one of those is set, the plain `attacks`/
    `strength`/`damage` int sitting beside it is only a grouping/preview
    PLACEHOLDER - each of the three fields says exactly that in its own
    comment in game/weapons.py - and is never the value an attack resolves
    with; the real one is rolled as a visible dice step (ShootingController's
    "attacks"/"strength" pending steps, DamageAllocationSession's
    pending_damage_roll).

    Reported: this table printed those placeholders, so the C'tan Shard of
    the Void Dragon's spear read "8" for a printed D6+2, the Plagueburst
    Crawler's entropy cannon "4" for D6+1, and the Myphitic Blight-hauler's
    multi-melta "3" for D6. The dice being ROLLED were right the whole time -
    only the card lied, and it lied for every weapon carrying a notation, in
    the A and S columns just as much as in the reported D one.
    """
    notation = getattr(weapon, which + "_notation", None)
    if notation is not None:
        return describe_dice_notation(notation)
    return str(getattr(weapon, which))


class UnitDatacardOverlay:
    """A full Warhammer-style datacard for whichever model the mouse is over,
    positioned next to the cursor - the unit's stat block, one table per
    weapon type it carries (Ranged/Melee), and its PRINTED abilities, laid out
    like a real 10th-edition datasheet.

    Opens two ways (see update_hover()): CTRL+hover at once, or by resting on
    a model for a moment without clicking. Scrolls with the wheel when the
    datasheet is longer than the window."""

    def __init__(self):
        self.name_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.section_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1, bold=True)
        self.label_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3, bold=True)
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)
        self.ability_title_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2, bold=True)
        self.keyword_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 4)
        self.hint_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 5)
        # Scroll state, keyed on the token it belongs to: moving to another
        # model starts that card at the top instead of inheriting an offset
        # measured against a different (possibly much shorter) card.
        self.scroll = 0
        self._scrolled_token = None
        self._scroll_max = 0
        # Dwell-to-open state, driven by update_hover().
        self._dwell_token = None
        self._dwell_since = None
        self._dwell_pos = (0, 0)
        self.visible = False
        # Where the card last landed. It is repositioned to stay on screen (a
        # tall card is pinned to the bottom edge, nowhere near the cursor), so
        # this is the only honest answer to "where is it" - anything computed
        # from the mouse position alone is a guess.
        self.last_rect = None

    # ------------------------------------------------------- when to show it

    def update_hover(self, token, mouse_pos, ctrl_held, mouse_down, now_ms):
        """Decide whether the card is open this frame; returns that bool.

        POLLED once per frame from main.py rather than driven by KEYDOWN/
        MOUSEMOTION events, for the reason this repo has hit five times
        (CLAUDE.md's Fehlerklasse 15): main.py's event chain is a ~48-branch
        if/elif over CONTROLLER STATE whose bodies almost all handle only
        mouse clicks, so anything hanging off the back of it is swallowed the
        moment any prompt is pending. A poll cannot be swallowed - and it also
        cannot strand a held modifier "down" across an ALT+TAB, which is the
        argument update_measuring() already writes out for the ALT ruler.

        Two ways in, on purpose:
          - CTRL + hover opens it AT ONCE. That is the existing gesture and it
            is unchanged; a player who knows the shortcut must not be made to
            wait for a timer.
          - Resting on a model for HOVER_DELAY_MS with no button down opens it
            by itself (user: "zum einen haette ich das overlay gerne wenn man
            ein paar Sekunden ueber die Einheit hovert und nichts klickt").

        The dwell timer resets on a different model, on leaving the models
        entirely, on any mouse button, and on cursor movement beyond
        HOVER_JITTER_PX. That jitter allowance is what makes it usable: a hand
        resting on a mouse moves it a pixel or two, and demanding a perfectly
        frozen cursor for a second would mean the card almost never appeared.
        """
        if token is None or mouse_down:
            self._dwell_token = None
            self._dwell_since = None
            self.visible = bool(ctrl_held) and token is not None and not mouse_down
            return self.visible

        moved = (abs(mouse_pos[0] - self._dwell_pos[0]) > HOVER_JITTER_PX
                 or abs(mouse_pos[1] - self._dwell_pos[1]) > HOVER_JITTER_PX)
        if token is not self._dwell_token or moved:
            self._dwell_token = token
            self._dwell_since = now_ms
            self._dwell_pos = mouse_pos

        dwelt = self._dwell_since is not None and now_ms - self._dwell_since >= HOVER_DELAY_MS
        self.visible = bool(ctrl_held) or dwelt
        return self.visible

    def handle_scroll(self, dy):
        """One mouse-wheel notch. True if it was consumed - main.py offers the
        wheel here BEFORE the camera zoom, so a wheel over an open card scrolls
        the card instead of zooming the board underneath it."""
        if not self.visible or self._scroll_max <= 0:
            return False
        self.scroll = max(0, min(self._scroll_max, self.scroll - dy * SCROLL_STEP))
        return True

    def _reset_scroll(self, token):
        if token is not self._scrolled_token:
            self._scrolled_token = token
            self.scroll = 0

    # -------------------------------------------------------------- the card

    def draw(self, surface, token, mouse_pos, transport_controller=None):
        if token.profile is None:
            return

        self._reset_scroll(token)
        stat_rows = token.profile.stat_rows(token.current_wounds)
        ranged_weapons = [w for w in token.weapons if w.weapon_type != MELEE]
        melee_weapons = [w for w in token.weapons if w.weapon_type == MELEE]
        cargo_lines = self._cargo_lines(token, transport_controller)
        attached_lines = self._attached_lines(token)
        enhancement_lines = self._enhancement_lines(token)
        ability_groups = self._ability_groups(token)

        content_height = self._content_height(
            token, stat_rows, ranged_weapons, melee_weapons, cargo_lines, attached_lines,
            enhancement_lines, ability_groups,
        )
        # The card now routinely outgrows the window - a datasheet's full
        # printed ability text runs to several paragraphs - so it is capped at
        # what fits and the remainder scrolls. User: "wahrscheinlich muss fuer
        # das groesser werdende overlay dann eine scroll Funktion eingebaut
        # werden."
        screen_rect = surface.get_rect()
        max_height = max(MIN_CARD_HEIGHT, screen_rect.height - 2 * SCREEN_MARGIN)
        height = min(content_height, max_height)
        scrollable = content_height > height
        footer = self.hint_font.get_height() + 6 if scrollable else 0
        # The footer eats into the visible content, so the last line still has
        # somewhere to scroll to once the hint covers it.
        self._scroll_max = max(0, content_height - height + footer) if scrollable else 0
        self.scroll = max(0, min(self.scroll, self._scroll_max))

        box_rect = pygame.Rect(0, 0, BOX_WIDTH, height)
        box_rect.topleft = (mouse_pos[0] + MOUSE_OFFSET, mouse_pos[1] + MOUSE_OFFSET)
        self._keep_on_screen(box_rect, screen_rect, mouse_pos)
        self.last_rect = box_rect.copy()

        pygame.draw.rect(surface, BOX_BG_COLOR, box_rect)
        pygame.draw.rect(surface, BOX_BORDER_COLOR, box_rect, width=2)

        # Everything below is drawn at a NEGATIVE offset once scrolled, so it
        # has to be clipped to the card or it would paint over the board.
        prev_clip = surface.get_clip()
        content_rect = pygame.Rect(box_rect.x + 1, box_rect.y + 1,
                                   box_rect.width - 2, box_rect.height - 2 - footer)
        surface.set_clip(content_rect.clip(prev_clip) if prev_clip else content_rect)

        y = box_rect.y + PADDING - self.scroll
        y = draw_wrapped_text(
            surface, self.name_font, token.profile.name, NAME_COLOR,
            box_rect.x + PADDING, y, self._text_width(), line_height=self.name_font.get_height() + 2,
        )

        if token.squad is not None:
            y = draw_wrapped_text(
                surface, self.font, self._squad_label(token), TEXT_COLOR,
                box_rect.x + PADDING, y, self._text_width(), line_height=ROW_HEIGHT,
            )
        y += 4

        if enhancement_lines:
            y = self._draw_cargo_section(surface, box_rect, y, enhancement_lines)
        if attached_lines:
            y = self._draw_cargo_section(surface, box_rect, y, attached_lines)
        if cargo_lines:
            y = self._draw_cargo_section(surface, box_rect, y, cargo_lines)

        y = self._draw_columns(
            surface, box_rect, y,
            [label for label, _ in stat_rows], [str(value) for _, value in stat_rows],
        )

        if ranged_weapons:
            # Almost every weapon uses the model's own BS, but a few (e.g.
            # Strike Team's Support Turret) print their own, worse BS - see
            # effective_ballistic_skill().
            y = self._draw_weapon_table(
                surface, box_rect, y, "RANGED WEAPONS", ranged_weapons,
                lambda w: effective_ballistic_skill(token, w), "BS",
            )
        if melee_weapons:
            # Almost every weapon uses the model's own WS, but a few (e.g.
            # Power Klaw) print their own, worse WS - see
            # effective_weapon_skill().
            y = self._draw_weapon_table(
                surface, box_rect, y, "MELEE WEAPONS", melee_weapons, lambda w: effective_weapon_skill(token, w), "WS",
            )

        if ability_groups:
            self._draw_abilities(surface, box_rect, y, ability_groups)

        surface.set_clip(prev_clip)

        if scrollable:
            self._draw_scroll_chrome(surface, box_rect, content_height, height, footer)

    # ---------------------------------------------------------- abilities

    def _ability_groups(self, token):
        """[(heading or None, [rules_text.Ability])] - the unit's PRINTED
        rules, read out of the rules/ corpus.

        Deliberately NOT Datasheet.abilities_text: that field is a developer
        note whose fidelity varies per faction by design (Orks near-verbatim,
        Aeldari a paraphrase ending in "- see game/bladestorm.py"), and the
        user asked for "die original regeltexte... keine selbst generierten
        varianten". See game/rules_text.py.

        ONE GROUP PER COMPONENT for an attached unit (19.01), because a merged
        unit genuinely has several datasheets' abilities live at once and a
        single squad.datasheet describes only one of them - hovering a Boy
        would otherwise never show that the Warboss in the same unit brings
        Waaagh!. The heading is dropped for a plain unit, where there is only
        one datasheet and naming it would just repeat the card's own title.
        Components are deduplicated by datasheet: two Warlock Conclaves merged
        into one unit print one set of rules, not two identical ones."""
        squad = getattr(token, "squad", None)
        if squad is None:
            return []
        if attached_units.is_attached_unit(squad):
            groups, seen = [], set()
            for component in attached_units.components(squad):
                datasheet = getattr(component, "datasheet", None)
                if datasheet is None or id(datasheet) in seen:
                    continue
                seen.add(id(datasheet))
                abilities = rules_text.abilities_for(datasheet)
                if abilities:
                    groups.append((component.name, abilities))
            return groups
        abilities = rules_text.abilities_for(getattr(squad, "datasheet", None))
        return [(None, abilities)] if abilities else []

    def _ability_line_height(self):
        return self.font.get_height() + 2

    def _abilities_height(self, groups):
        text_width = self._text_width()
        line_height = self._ability_line_height()
        height = self.section_font.get_height() + 4
        for heading, abilities in groups:
            if heading:
                height += self.label_font.get_height() + 3
            for ability in abilities:
                height += self._ability_height(ability, text_width, line_height)
        return height + SECTION_GAP

    def _ability_height(self, ability, text_width, line_height):
        """Measured against the SAME wrapping _draw_ability() uses - the
        hazard this card already carries a comment about, now over text that
        is paragraphs long rather than one line."""
        height = 0
        if ability.label:
            height += wrapped_text_height(self.font, f"{ability.label}: {ability.body}",
                                          text_width, line_height=line_height)
        else:
            if ability.title:
                height += wrapped_text_height(self.ability_title_font, ability.title,
                                              text_width, line_height=line_height)
            if ability.body:
                height += wrapped_text_height(self.font, ability.body, text_width,
                                              line_height=line_height)
            for bullet in ability.bullets:
                height += wrapped_text_height(self.font, f"- {bullet}",
                                              text_width - BULLET_INDENT, line_height=line_height)
        return height + ABILITY_GAP

    def _draw_abilities(self, surface, box_rect, y, groups):
        title_surf = self.section_font.render("ABILITIES", True, HEADER_COLOR)
        surface.blit(title_surf, (box_rect.x + PADDING, y))
        y += title_surf.get_height() + 4

        text_width = self._text_width()
        line_height = self._ability_line_height()
        for heading, abilities in groups:
            if heading:
                head_surf = self.label_font.render(heading.upper(), True, ABILITY_LABEL_COLOR)
                surface.blit(head_surf, (box_rect.x + PADDING, y))
                y += head_surf.get_height() + 3
            for ability in abilities:
                y = self._draw_ability(surface, box_rect, y, ability, text_width, line_height)
        return y + SECTION_GAP

    def _draw_ability(self, surface, box_rect, y, ability, text_width, line_height):
        x = box_rect.x + PADDING
        if ability.label:
            # "CORE: Deep Strike, Leader" - one row, drawn as one wrapped
            # string so a long CORE list still wraps cleanly.
            y = draw_wrapped_text(surface, self.font, f"{ability.label}: {ability.body}",
                                  ABILITY_LABEL_COLOR, x, y, text_width, line_height=line_height)
            return y + ABILITY_GAP
        if ability.title:
            y = draw_wrapped_text(surface, self.ability_title_font, ability.title,
                                  ABILITY_TITLE_COLOR, x, y, text_width, line_height=line_height)
        if ability.body:
            y = draw_wrapped_text(surface, self.font, ability.body, TEXT_COLOR,
                                  x, y, text_width, line_height=line_height)
        for bullet in ability.bullets:
            y = draw_wrapped_text(surface, self.font, f"- {bullet}", TEXT_COLOR,
                                  x + BULLET_INDENT, y, text_width - BULLET_INDENT,
                                  line_height=line_height)
        return y + ABILITY_GAP

    # ------------------------------------------------------------ scrolling

    def _draw_scroll_chrome(self, surface, box_rect, content_height, height, footer):
        """A track-and-thumb bar down the right edge plus a footer hint.

        Both, not one: the bar says HOW MUCH more there is and where you are,
        the hint says the card is scrollable at all. Without the hint a player
        who has never scrolled one of these has no reason to try the wheel;
        without the bar a long datasheet gives no sense of its length."""
        track = pygame.Rect(box_rect.right - SCROLLBAR_WIDTH - 3, box_rect.y + 3,
                            SCROLLBAR_WIDTH, box_rect.height - 6 - footer)
        pygame.draw.rect(surface, SCROLLBAR_TRACK_COLOR, track, border_radius=2)
        visible_fraction = min(1.0, height / float(content_height))
        thumb_height = max(18, int(track.height * visible_fraction))
        travel = track.height - thumb_height
        progress = (self.scroll / float(self._scroll_max)) if self._scroll_max else 0.0
        thumb = pygame.Rect(track.x, track.y + int(travel * progress), track.width, thumb_height)
        pygame.draw.rect(surface, SCROLLBAR_COLOR, thumb, border_radius=2)

        hint = "scroll for more" if self.scroll < self._scroll_max else "scroll wheel"
        hint_surf = self.hint_font.render(hint, True, HINT_COLOR)
        footer_rect = pygame.Rect(box_rect.x + 1, box_rect.bottom - footer - 1,
                                  box_rect.width - 2, footer)
        pygame.draw.rect(surface, BOX_BG_COLOR, footer_rect)
        pygame.draw.line(surface, TABLE_LINE_COLOR,
                         (footer_rect.x + PADDING, footer_rect.y),
                         (footer_rect.right - PADDING, footer_rect.y))
        surface.blit(hint_surf, hint_surf.get_rect(
            centerx=footer_rect.centerx, centery=footer_rect.centery + 1))

    def _text_width(self):
        """Usable text width inside the card - every line here (unit name,
        squad line, attached/cargo lists) is data-driven, so all of them
        wrap against this instead of trusting the string to be short. An
        attached unit's name (19.01) alone is routinely wider than the
        card."""
        return BOX_WIDTH - 2 * PADDING

    def _squad_label(self, token):
        # Points are the UNIT's cost, not this model's - hence on the squad
        # line rather than beside the model name. Omitted entirely when
        # unpriced (no points list for that faction yet, see
        # game/factions/points.py) rather than shown as "0 pts".
        label = f"Squad: {token.squad.name}"
        if token.squad.points is not None:
            label += f" ({token.squad.points} pts)"
        return label

    def _keep_on_screen(self, box_rect, screen_rect, mouse_pos):
        if box_rect.right > screen_rect.right:
            box_rect.right = mouse_pos[0] - MOUSE_OFFSET // 2
        if box_rect.bottom > screen_rect.bottom:
            box_rect.bottom = screen_rect.bottom - 4
        if box_rect.left < screen_rect.left:
            box_rect.left = screen_rect.left + 4
        if box_rect.top < screen_rect.top:
            box_rect.top = screen_rect.top + 4

    def _cargo_lines(self, token, transport_controller):
        """What's embarked inside this TRANSPORT right now, if anything -
        without this a player hovering a transport had no way to see what
        it's carrying (rule 18.02/18.04 concern - capacity and disembark
        options both depend on it)."""
        if transport_controller is None or not token.profile.transport:
            return []
        squads = transport_controller.embarked_squads_in(token)
        if not squads:
            return []
        used = transport_controller.embarked_model_count(token)
        capacity = token.profile.transport_capacity
        lines = [f"Transporting ({used}/{capacity} capacity):"]
        for squad in squads:
            lines.append(f"  {squad.name} ({len(squad.models)} models)")
        return lines

    def _attached_lines(self, token):
        """What this attached unit (19.01) is made of, when the hovered model
        is part of one.

        Hovering shows ONE model's datacard, which for an attached unit is
        only ever part of the story - the whole point of the merge is that a
        Warboss and ten Boyz are one unit now, and a player looking at a Boy
        has no other way to see that the Warboss is in there (nor, hovering
        the Warboss, that it is no longer a unit of its own). Each component
        is listed with its surviving model count, so the two things that
        actually change during a game - which component is nearly gone, and
        whether the character is still alive - are both visible. A component
        whose models are all dead is still listed, struck down to 0/N rather
        than dropped, because rule 19.04 keys ability loss to exactly that
        transition."""
        squad = token.squad
        if squad is None or not attached_units.is_attached_unit(squad):
            return []
        lines = ["Attached unit (19.01):"]
        for component in attached_units.components(squad):
            alive = len(component.alive_models())
            total = len(component.starting_models)
            role = "" if component.role == attached_units.BODYGUARD else f" [{component.role.upper()}]"
            lines.append(f"  {component.name}{role} - {alive}/{total} models")
        return lines

    def _enhancement_lines(self, token):
        """Which Enhancement this specific MODEL carries, if any.

        Per model, not per unit: an Enhancement is given to one model, and in
        an attached unit (19.01) the whole point of hovering is to find out
        which of the merged models is which - listing it on all of them would
        say the opposite of what is true. Its points are shown because that is
        the other half of what an Enhancement is."""
        if token.profile is None:
            return []
        # Read off game/enhancements.py's registry rather than one named flag:
        # nineteen are wired, and a card that could only ever show the first
        # would be silently wrong for the other eighteen.
        carried = [spec for spec in enhancements.ENHANCEMENTS.values()
                   if getattr(token.profile, spec.flag, False)]
        if not carried:
            return []
        return ["Enhancement:"] + [f"  {spec.name} ({spec.points} pts)" for spec in carried]

    def _content_height(self, token, stat_rows, ranged_weapons, melee_weapons, cargo_lines=(),
                        attached_lines=(), enhancement_lines=(), ability_groups=()):
        """Measured against the SAME wrapping the drawing does - a card
        sized for one line per entry while the text needs two would clip
        its own last section."""
        text_width = self._text_width()
        height = PADDING  # top
        height += wrapped_text_height(
            self.name_font, token.profile.name, text_width, line_height=self.name_font.get_height() + 2,
        )
        if token.squad is not None:
            height += wrapped_text_height(self.font, self._squad_label(token), text_width, line_height=ROW_HEIGHT)
        height += 4
        for lines in (enhancement_lines, attached_lines, cargo_lines):
            if lines:
                height += self._section_height(lines) + SECTION_GAP
        height += ROW_HEIGHT * 2 + SECTION_GAP  # stat table: header row + value row
        if ranged_weapons:
            height += self.section_font.get_height() + 4 + self._weapon_table_height(ranged_weapons) + SECTION_GAP
        if melee_weapons:
            height += self.section_font.get_height() + 4 + self._weapon_table_height(melee_weapons) + SECTION_GAP
        if ability_groups:
            height += self._abilities_height(ability_groups)
        height += PADDING - SECTION_GAP  # bottom margin (last section already added a gap)
        return height

    def _section_height(self, lines):
        line_height = self.font.get_height() + 2
        return sum(
            wrapped_text_height(self.font, line, self._text_width(), line_height=line_height) for line in lines
        )

    def _weapon_keyword_lines(self, weapon, box_rect=None):
        """This weapon's printed keywords, wrapped to the FULL table width.

        Reported: "in den weapon info tabellen im overlay fehlen die keywords
        (zb twin linked oder sustained hits)". They get a line of their own
        under the row's numbers rather than an eighth column, and the width is
        the reason: the widest keyword string any built weapon prints
        ("ANTI-INFANTRY 2+, BLAST, HAZARDOUS, IGNORES COVER, PSYCHIC") measures
        346 px, which fits the 432 px table on ONE line and would need four
        inside a 132 px name cell. Measured, not assumed - see
        test_unit_datacard.py section 10.

        A weapon with no keywords costs nothing: its row stays exactly the
        height it was before."""
        keywords = printed_keywords(weapon)
        if not keywords:
            return []
        width = (box_rect.width if box_rect is not None else BOX_WIDTH) - 2 * PADDING - 8
        text = ", ".join(keywords)
        return wrap_text(self.keyword_font, text, width) or [text]

    def _weapon_band_height(self, weapon):
        """The height of a row's NUMBERS band - the name plus the six values.

        Kept apart from the row height below because the column separators are
        drawn through this band only: a vertical line running on through the
        keyword line would cut the keywords into pieces belonging to columns
        they have nothing to do with."""
        lines = len(wrap_text(self.font, weapon.name, NAME_COLUMN_WIDTH - 8) or [weapon.name])
        return max(ROW_HEIGHT, lines * (self.font.get_height() + 2) + 6)

    def _weapon_row_height(self, weapon, box_rect=None):
        """A weapon's name is the one table cell that carries a long string
        ("Twin Pulse Carbine", "Cyclic Ion Raker (Overcharge)"), so its row
        grows for a wrapped name instead of the name spilling over the next
        column's numbers - and again for its keyword line."""
        height = self._weapon_band_height(weapon)
        keyword_lines = self._weapon_keyword_lines(weapon, box_rect)
        if keyword_lines:
            height += len(keyword_lines) * (self.keyword_font.get_height() + 1) + 4
        return height

    def _weapon_table_height(self, weapons):
        return ROW_HEIGHT + sum(self._weapon_row_height(w) for w in weapons)

    def _column_layout(self, box_rect, column_count, name_column=False):
        table_width = box_rect.width - 2 * PADDING
        if name_column:
            other_width = (table_width - NAME_COLUMN_WIDTH) / (column_count - 1)
            widths = [NAME_COLUMN_WIDTH] + [other_width] * (column_count - 1)
        else:
            widths = [table_width / column_count] * column_count
        positions = []
        x = box_rect.x + PADDING
        for w in widths:
            positions.append(x)
            x += w
        return widths, positions

    def _draw_columns(self, surface, box_rect, y, headers, values):
        """The M/WS/BS/T/W/Ld/Sv/OC stat block: one evenly-spaced column per
        stat, header row on top of the value row, like a real datasheet."""
        widths, positions = self._column_layout(box_rect, len(headers))
        table_rect = pygame.Rect(box_rect.x + PADDING, y, box_rect.width - 2 * PADDING, ROW_HEIGHT * 2)
        pygame.draw.rect(surface, TABLE_LINE_COLOR, table_rect, width=1)
        pygame.draw.line(
            surface, TABLE_LINE_COLOR,
            (table_rect.x, table_rect.y + ROW_HEIGHT), (table_rect.right, table_rect.y + ROW_HEIGHT),
        )
        for i, (w, x) in enumerate(zip(widths, positions)):
            if i > 0:
                pygame.draw.line(surface, TABLE_LINE_COLOR, (x, table_rect.y), (x, table_rect.bottom))
            header_surf = self.label_font.render(headers[i], True, HEADER_COLOR)
            surface.blit(header_surf, header_surf.get_rect(center=(x + w / 2, table_rect.y + ROW_HEIGHT // 2)))
            value_surf = self.font.render(values[i], True, TEXT_COLOR)
            surface.blit(value_surf, value_surf.get_rect(center=(x + w / 2, table_rect.y + ROW_HEIGHT + ROW_HEIGHT // 2)))
        return table_rect.bottom + SECTION_GAP

    def _draw_cargo_section(self, surface, box_rect, y, cargo_lines):
        for i, line in enumerate(cargo_lines):
            color = HEADER_COLOR if i == 0 else TEXT_COLOR
            y = draw_wrapped_text(
                surface, self.font, line, color, box_rect.x + PADDING, y, self._text_width(),
                line_height=self.font.get_height() + 2,
            )
        return y + SECTION_GAP

    def _draw_weapon_table(self, surface, box_rect, y, title, weapons, skill_for, skill_label):
        title_surf = self.section_font.render(title, True, HEADER_COLOR)
        surface.blit(title_surf, (box_rect.x + PADDING, y))
        y += title_surf.get_height() + 4

        columns = ["Weapon", "Range", "A", skill_label, "S", "AP", "D"]
        widths, positions = self._column_layout(box_rect, len(columns), name_column=True)
        row_heights = [self._weapon_row_height(w, box_rect) for w in weapons]
        band_heights = [self._weapon_band_height(w) for w in weapons]
        table_rect = pygame.Rect(
            box_rect.x + PADDING, y, box_rect.width - 2 * PADDING, ROW_HEIGHT + sum(row_heights),
        )
        pygame.draw.rect(surface, TABLE_LINE_COLOR, table_rect, width=1)
        pygame.draw.line(
            surface, TABLE_LINE_COLOR,
            (table_rect.x, table_rect.y + ROW_HEIGHT), (table_rect.right, table_rect.y + ROW_HEIGHT),
        )

        # The column separators run through the header and through each row's
        # NUMBERS band, and stop there - see _weapon_band_height().
        bands = [(table_rect.y, table_rect.y + ROW_HEIGHT)]
        band_top = table_rect.y + ROW_HEIGHT
        for band_height, row_height in zip(band_heights, row_heights):
            bands.append((band_top, band_top + band_height))
            band_top += row_height
        for top, bottom in bands:
            for i, x in enumerate(positions):
                if i > 0:
                    pygame.draw.line(surface, TABLE_LINE_COLOR, (x, top), (x, bottom))

        self._draw_row(surface, widths, positions, table_rect.y, ROW_HEIGHT, columns, self.label_font, HEADER_COLOR)

        row_y = table_rect.y + ROW_HEIGHT
        for index, weapon in enumerate(weapons):
            # A rule between weapons: with a keyword line hanging under some
            # rows and not others, "where does this row end" stops being
            # obvious from the numbers alone.
            if index:
                pygame.draw.line(surface, TABLE_LINE_COLOR,
                                 (table_rect.x, row_y), (table_rect.right, row_y))
            range_label = "Melee" if weapon.weapon_type == MELEE else f'{weapon.range_in}"'
            values = [
                weapon.name, range_label, printed_characteristic(weapon, "attacks"),
                str(skill_for(weapon)), printed_characteristic(weapon, "strength"),
                str(weapon.ap), printed_characteristic(weapon, "damage"),
            ]
            self._draw_row(surface, widths, positions, row_y, band_heights[index], values,
                           self.font, TEXT_COLOR)
            keyword_y = row_y + band_heights[index] + 2
            for line in self._weapon_keyword_lines(weapon, box_rect):
                surface.blit(self.keyword_font.render(line, True, KEYWORD_COLOR),
                             (table_rect.x + 4, keyword_y))
                keyword_y += self.keyword_font.get_height() + 1
            row_y += row_heights[index]

        return table_rect.bottom + SECTION_GAP

    def _draw_row(self, surface, widths, positions, row_y, row_height, values, font, color):
        for i, (w, x, val) in enumerate(zip(widths, positions, values)):
            if i == 0:
                # The name column is the only left-aligned, wrappable one -
                # the rest are short numbers centered in their column.
                lines = wrap_text(font, val, w - 8) or [val]
                line_height = font.get_height() + 2
                line_y = row_y + (row_height - len(lines) * line_height) // 2
                for line in lines:
                    surface.blit(font.render(line, True, color), (x + 4, line_y))
                    line_y += line_height
            else:
                val_surf = font.render(val, True, color)
                surface.blit(val_surf, val_surf.get_rect(center=(x + w / 2, row_y + row_height // 2)))
