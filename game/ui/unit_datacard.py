import pygame

from game import attached_units, config, starflare_ignition
from game.fight import effective_weapon_skill
from game.shooting import effective_ballistic_skill
from game.ui.text_utils import draw_wrapped_text, wrap_text, wrapped_text_height
from game.weapons import MELEE

BOX_BG_COLOR = (25, 25, 25)
BOX_BORDER_COLOR = (255, 215, 0)
NAME_COLOR = (255, 215, 0)
TEXT_COLOR = (230, 230, 230)
HEADER_COLOR = config.PANEL_HEADER_COLOR
TABLE_LINE_COLOR = (90, 90, 90)

BOX_WIDTH = 460
PADDING = 14
ROW_HEIGHT = 24
SECTION_GAP = 10
NAME_COLUMN_WIDTH = 140

MOUSE_OFFSET = 24


class UnitDatacardOverlay:
    """Ctrl+hover: a full Warhammer-style datacard for whichever model the
    mouse is over, positioned next to the cursor - the unit's full stat
    block plus one table per weapon type it carries (Ranged/Melee), laid
    out like a real 10th-edition datasheet."""

    def __init__(self):
        self.name_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 4, bold=True)
        self.section_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1, bold=True)
        self.label_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 3, bold=True)
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 2)

    def draw(self, surface, token, mouse_pos, transport_controller=None):
        if token.profile is None:
            return

        stat_rows = token.profile.stat_rows(token.current_wounds)
        ranged_weapons = [w for w in token.weapons if w.weapon_type != MELEE]
        melee_weapons = [w for w in token.weapons if w.weapon_type == MELEE]
        cargo_lines = self._cargo_lines(token, transport_controller)
        attached_lines = self._attached_lines(token)
        enhancement_lines = self._enhancement_lines(token)

        height = self._content_height(
            token, stat_rows, ranged_weapons, melee_weapons, cargo_lines, attached_lines,
            enhancement_lines,
        )
        box_rect = pygame.Rect(0, 0, BOX_WIDTH, height)
        box_rect.topleft = (mouse_pos[0] + MOUSE_OFFSET, mouse_pos[1] + MOUSE_OFFSET)
        self._keep_on_screen(box_rect, surface.get_rect(), mouse_pos)

        pygame.draw.rect(surface, BOX_BG_COLOR, box_rect)
        pygame.draw.rect(surface, BOX_BORDER_COLOR, box_rect, width=2)

        y = box_rect.y + PADDING
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
        if token.profile is None or not getattr(token.profile, "starflare_ignition_system", False):
            return []
        return [
            "Enhancement:",
            f"  {starflare_ignition.STARFLARE_IGNITION_SYSTEM_NAME} "
            f"({starflare_ignition.STARFLARE_IGNITION_SYSTEM_POINTS} pts)",
        ]

    def _content_height(self, token, stat_rows, ranged_weapons, melee_weapons, cargo_lines=(),
                        attached_lines=(), enhancement_lines=()):
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
        height += PADDING - SECTION_GAP  # bottom margin (last section already added a gap)
        return height

    def _section_height(self, lines):
        line_height = self.font.get_height() + 2
        return sum(
            wrapped_text_height(self.font, line, self._text_width(), line_height=line_height) for line in lines
        )

    def _weapon_row_height(self, weapon):
        """A weapon's name is the one table cell that carries a long string
        ("Twin Pulse Carbine", "Cyclic Ion Raker (Overcharge)"), so its row
        grows for a wrapped name instead of the name spilling over the next
        column's numbers."""
        lines = len(wrap_text(self.font, weapon.name, NAME_COLUMN_WIDTH - 8) or [weapon.name])
        return max(ROW_HEIGHT, lines * (self.font.get_height() + 2) + 6)

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
        row_heights = [self._weapon_row_height(w) for w in weapons]
        table_rect = pygame.Rect(
            box_rect.x + PADDING, y, box_rect.width - 2 * PADDING, ROW_HEIGHT + sum(row_heights),
        )
        pygame.draw.rect(surface, TABLE_LINE_COLOR, table_rect, width=1)
        pygame.draw.line(
            surface, TABLE_LINE_COLOR,
            (table_rect.x, table_rect.y + ROW_HEIGHT), (table_rect.right, table_rect.y + ROW_HEIGHT),
        )
        for i, x in enumerate(positions):
            if i > 0:
                pygame.draw.line(surface, TABLE_LINE_COLOR, (x, table_rect.y), (x, table_rect.bottom))

        self._draw_row(surface, widths, positions, table_rect.y, ROW_HEIGHT, columns, self.label_font, HEADER_COLOR)

        row_y = table_rect.y + ROW_HEIGHT
        for weapon, row_height in zip(weapons, row_heights):
            range_label = "Melee" if weapon.weapon_type == MELEE else f'{weapon.range_in}"'
            values = [
                weapon.name, range_label, str(weapon.attacks),
                str(skill_for(weapon)), str(weapon.strength), str(weapon.ap), str(weapon.damage),
            ]
            self._draw_row(surface, widths, positions, row_y, row_height, values, self.font, TEXT_COLOR)
            row_y += row_height

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
