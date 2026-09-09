"""The printed rule behind a board pick, shown in the LEFT column - under
the ability's own name and the way out, where the question already is.

User: "immer wenn ich aufgefordert werde durch eine Fähigkeit etwas auf dem
Spielfeld auszuwählen. zb. bei necron immortals oder deathguard, schreibe die
Fähigkeit Regel mit in die rechte Spalte, sonst weiß ich gar nicht was ich da
auswähle."

A board pick (game/unit_pick.py) deliberately draws no overlay - it would sit
on the units that have to be clicked - so the whole explanation was the left
panel's one-line prompt: "Living Lightning - strike which unit?".

Both named examples are covered here as the boundary cases they are:
  * NECRON IMMORTALS is a rule 19.01 merge, and the ability asking is the
    LEADER's. Looking only at squad.datasheet finds the Immortals' sheet and
    misses Living Lightning entirely - so the component half of the lookup is
    tested directly rather than through a unit that happens to work either way.
  * DEATH GUARD (the Defiler's Barrage of Filth) is the plain, unmerged case.

Run: python test_decision_rule_panel.py
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1600, 900))

import testkit as tk

# Asked for by FACTION, not named: a suite that hardcodes a list key breaks
# when that list is retired, and breaks as a crash rather than a red line.
DG_LIST = tk.list_key("DEATH GUARD")
from game import army_lists, config, maps, prompt_rule, rules_text
from game.turn import TurnTracker
from game.ui import button_style, rules_body
from game.ui.game_status_panel import GameStatusPanel

maps.apply_to_config(maps.get("map2"))

c = tk.Checks("the rule behind a board pick")

LIVING_LIGHTNING = "1 Immortals 1 + Plasmancer: Living Lightning - strike which unit?"
BARRAGE = "1 Defiler 1: Barrage of Filth - which unit is easier to hurt?"


def army(key):
    entry = army_lists.get(key)
    return entry, army_lists.preview_squads(key, "Player 1")


def look_up(key, prompt, squads=None):
    entry, built = army(key)
    return prompt_rule.for_prompt(prompt, squads if squads is not None else built,
                                  entry.faction_keyword, entry.detachments)


# ------------------------------------------------------------------ 1) lookup
print("\n1) The two reported prompts resolve to their printed rule")
name, blocks = look_up("necrons", LIVING_LIGHTNING)
c.eq("NECRON IMMORTALS: the leader's ability is found", name, "Living Lightning")
c.true("...and it has printed text", bool(blocks))
name_dg, blocks_dg = look_up(DG_LIST, BARRAGE)
c.eq("DEATH GUARD: the Defiler's ability is found", name_dg, "Barrage of Filth")
c.true("...and it has printed text", bool(blocks_dg))

# VERBATIM, the same guarantee the hover datacard is held to: every word shown
# has to be in the corpus file. A test that only checked "some text came back"
# would pass for a paraphrase, which is the thing this repo keeps out.
sheets = prompt_rule._datasheets([s for s in army("necrons")[1]
                                  if s.name.startswith("1 Immortals 1")])
plasmancer = [d for d in sheets if d.name == "Plasmancer"]
c.eq("the merged unit exposes its leader's datasheet", len(plasmancer), 1)
# Everything below degrades to RED rather than raising when the lookup finds
# nothing: an A/B probe that crashes the suite hides WHICH check it broke -
# a lesson this repo has now recorded a dozen times.
leader = plasmancer[0] if plasmancer else None
corpus = ""
if leader is not None:
    corpus = rules_text._strip_markdown(
        " ".join(open(rules_text.rules_path(leader), encoding="utf-8").read().split()))
missing = [b.text for b in blocks if b.text and b.text not in corpus]
c.eq("every drawn line is verbatim from the corpus file", missing, [])
c.true("the rule really says what the prompt is asking about",
       any("select one enemy unit" in b.text.lower() for b in blocks))

print("\n1b) It gives nothing rather than guessing")
c.eq("a prompt naming no printed rule", look_up("necrons", "pick a unit, any unit")[0], None)
c.eq("an empty prompt", look_up("necrons", "")[0], None)
# Word boundaries: without them a rule called "Guide" would answer for
# "Guided", and the panel would explain the wrong rule with full confidence.
c.true("a name inside a longer word does not match",
       not prompt_rule._mentioned("the unit is Guided by a marker", "Guide"))
c.true("...while the name on its own does",
       prompt_rule._mentioned("Farseer: Guide - which unit?", "Guide"))

print("\n1d) A printed name with a bracketed tag still resolves")
# 29 of the 264 printed ability titles end in "(Psychic)"/"(Aura)" while the
# prompt writes the bare name - and the psychic marks are board picks, i.e.
# exactly the shape this feature exists for.
GUIDE = "1 Guardian Defenders 1 + Farseer: Guide - select one enemy unit."
c.eq("the Farseer's Guide resolves from a prompt without the tag",
     look_up("aeldari", GUIDE)[0], "Guide (Psychic)")
FALLOUT = ("1 Plague Marines 1 + Malignant Plaguecaster: "
           "Pestilent Fallout - enfeeble which unit?")
c.eq("DEATH GUARD: Pestilent Fallout too",
     look_up(DG_LIST, FALLOUT)[0], "Pestilent Fallout (Psychic)")
c.eq("stripping the tag is what does it", prompt_rule._bare("Guide (Psychic)"), "Guide")
c.eq("...and a name without one is left alone", prompt_rule._bare("Living Lightning"), None)
c.true("the bare alias is still whole-word matched",
       not prompt_rule._mentioned("the unit is Guided by a marker", "Guide (Psychic)"))

print("\n1c) Only rules that are ON THE TABLE are candidates")
# The same prompt, asked against the WRONG army's units, must not resolve -
# otherwise the panel could explain a rule nobody is fielding.
c.eq("Living Lightning is not found among Death Guard units",
     look_up(DG_LIST, LIVING_LIGHTNING, army(DG_LIST)[1])[0], None)
c.eq("Barrage of Filth is not found among Necron units",
     look_up("necrons", BARRAGE, army("necrons")[1])[0], None)

print("\n2) ability_blocks() is the structured sibling of abilities_for()")
c.eq("an unknown ability name", rules_text.ability_blocks(leader, "No Such Rule"), [])
c.eq("no name at all", rules_text.ability_blocks(leader, ""), [])
c.true("the folded name matches regardless of case",
       bool(rules_text.ability_blocks(leader, "LIVING LIGHTNING")))
flat = " ".join(b.text for b in rules_text.ability_blocks(leader, "Living Lightning"))
card = [a for a in rules_text.abilities_for(leader) if a.title == "Living Lightning"]
c.eq("the card and the panel read the same ability", len(card), 1)
c.true("...and the same words", bool(card) and card[0].body.split(".")[0] in flat)


# ------------------------------------------------------------------ 3) pixels
# THE LEFT column, not the right. It was in the right panel because that is the
# emptier one; the user then asked for it to sit where the question already is:
# "'why you are choosing' soll in die linke spalte, nicht rechts". A board pick
# takes the whole left panel over (_draw_unit_pick_ui), so this renders that
# screen for real rather than a bare panel.
from game.ui import action_panel  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402
from game import unit_pick as unit_pick_mod  # noqa: E402
from game.decision import DecisionManager  # noqa: E402


class _Tok:
    def __init__(self, squad):
        self.squad = squad

    def is_dead(self):
        return False


_pick_squad = next(s for s in army("necrons")[1] if s.name.startswith("1 Immortals 1"))


def render_pick(pick, decision_rule, size=(1600, 900)):
    """The pick screen for a GIVEN record - so a section can hand it one the
    ordinary path does not produce (a rule that offers no way out)."""
    width, height = size
    surface = pygame.Surface((width, height))
    surface.fill((0, 0, 0))
    rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH,
                       height - getattr(config, "RESERVES_PANEL_HEIGHT", 0))
    # _draw_unit_pick_ui() draws only its own content; draw() is what fills the
    # panel. Filling it here is what makes "is anything drawn below y" mean
    # anything at all.
    surface.fill(config.PANEL_BG_COLOR, rect)
    panel = ActionPanel()
    panel._buttons = []
    panel._draw_unit_pick_ui(surface, rect, pick, decision_rule=decision_rule)
    return panel, surface, rect


def render(decision_rule, size=(1600, 900)):
    dm = DecisionManager()
    dm.request("Player 1", "Living Lightning - strike which unit?",
               [(_pick_squad.name, (lambda: None), _pick_squad),
                ("Decline", lambda: None)])
    # A token's .squad is the SQUAD, not the model - unit_pick reads it to
    # answer "is this unit on the board".
    pick = unit_pick_mod.pending(dm, [_Tok(_pick_squad) for _ in _pick_squad.models])
    return render_pick(pick, decision_rule, size=size)


def ink_below(surface, rect, y):
    """Rows below `y` carrying anything but the panel background."""
    bg = tuple(config.PANEL_BG_COLOR[:3])
    return [row for row in range(y, rect.bottom - 3)
            if any(surface.get_at((x, row))[:3] != bg
                   for x in range(rect.x + 3, rect.right - 3, 3))]


print()
print("3) The left panel draws it, under the pick screen, and only when there is one")
blocks = look_up("necrons", LIVING_LIGHTNING)[1]
plain_panel, plain, rect = render(None)
with_rule_panel, with_rule, _ = render(("Living Lightning", blocks))

# MEASURED, not guessed: where the pick screen itself stops depends on how
# many units are eligible and how many ways out the rule offers.
_plain_rows = ink_below(plain, rect, rect.y + 4)
_below = (max(_plain_rows) if _plain_rows else rect.y) + 6
c.true("without a rule, nothing is drawn below the pick screen",
       not ink_below(plain, rect, _below))
c.true("with one, something is", bool(ink_below(with_rule, rect, _below)))
c.eq("the rule box is recorded", bool(with_rule_panel._rule_bottom), True)

# NOTHING UNDER THE TITLE MOVED: the eligible-unit list and the way out are
# what the player is reading and reaching for when the prompt opens.
#
# The TITLE itself is now the rule's own name (see 3d), so it is EXPECTED to
# differ between the two renders - and that is checked first, because "the rest
# is identical" would otherwise pass just as well on a screen that never
# mentions the rule at all.
TITLE_BOTTOM = rect.y + button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT
c.true("the title itself says which rule this is",
       any(plain.get_at((x, y)) != with_rule.get_at((x, y))
           for y in range(rect.y + button_style.HEADER_MARGIN + 2, TITLE_BOTTOM, 2)
           for x in range(rect.x + 6, rect.right - 6, 2)))
# DERIVED, not a round number: the band runs from under the title to just
# above where the rule box's own header begins, so it covers the whole of the
# pick screen proper however tall this particular prompt happens to be.
#
# Everything here degrades to RED rather than raising: a probe that stops the
# box being drawn at all leaves _rule_view None, and an AttributeError mid-suite
# hides WHICH assurance it broke - a lesson this repo has recorded a dozen times.
_VIEW_TOP = getattr(with_rule_panel._rule_view, "top", None)
c.true("the rule box reports where it starts", _VIEW_TOP is not None)
RULE_TOP = ((_VIEW_TOP if _VIEW_TOP is not None else rect.bottom)
            - action_panel.RULE_BOX_PADDING - button_style.SUBHEADER_HEIGHT)
band = pygame.Rect(rect.x, TITLE_BOTTOM + 2, rect.width, RULE_TOP - TITLE_BOTTOM - 2)
c.true("the band really covers the pick screen", band.height > 100)
c.true("everything under the title is pixel-identical",
       all(plain.get_at((x, y)) == with_rule.get_at((x, y))
           for y in range(band.top + 1, band.bottom, 2)
           for x in range(band.left + 2, band.right - 2, 3)))

# It has to stay inside its own column: the units being picked are on the board.
c.true("no ink escapes to the right of the panel",
       all(with_rule.get_at((rect.right + 2, y))[:3] == (0, 0, 0)
           for y in range(rect.y + 2, rect.bottom - 2, 3)))
c.true("the box ends inside the panel",
       0 < (with_rule_panel._rule_bottom or 0) <= rect.bottom)

print()
print("3b) It fits the smallest window this project targets")
for size in ((1920, 1080), (1600, 900), (1280, 720)):
    panel, surface, prect = render(("Living Lightning", blocks), size=size)
    label = f"{size[0]}x{size[1]}"
    c.true(f"{label}: the rule is drawn", panel._rule_bottom is not None)
    c.true(f"{label}: and stays inside the panel", (panel._rule_bottom or 0) <= prect.bottom)

print()
print("3c) A long rule SCROLLS - this column has no room to clip one away")
# The right panel could clip: it had 336px of clear space. This one is already
# carrying the prompt, the unit list and the way out, so the rule has to stay
# readable rather than merely fit.
long_blocks = blocks * 12
tall_panel, tall, tall_rect = render(("Living Lightning", long_blocks), size=(1280, 720))
c.true("a long rule reports something to scroll", tall_panel._rule_scroll_max > 0)
c.eq("...and starts at the top", tall_panel._rule_scroll, 0)
# A probe that stops the box being drawn leaves this None, and reaching into it
# would abort the run instead of naming the assurance that broke - so the whole
# section falls back to a rect that claims nothing.
_view = tall_panel._rule_view or pygame.Rect(-99, -99, 1, 1)
c.true("the scrollable view is inside the panel",
       tall_panel._rule_view is not None and tall_rect.contains(_view))
c.true("a wheel notch over the box scrolls it",
       tall_panel.handle_rule_scroll(_view.center, -1) and tall_panel._rule_scroll > 0)
c.true("...and the wheel elsewhere is NOT claimed - the board still zooms",
       not tall_panel.handle_rule_scroll((_view.right + 400, _view.centery), -1))
_at = tall_panel._rule_scroll
for _ in range(200):
    tall_panel.handle_rule_scroll(_view.center, -1)
c.eq("scrolling stops at the end", tall_panel._rule_scroll, tall_panel._rule_scroll_max)
for _ in range(400):
    tall_panel.handle_rule_scroll(_view.center, 1)
c.eq("...and at the top", tall_panel._rule_scroll, 0)
short_panel, _s, _r = render(("Living Lightning", blocks), size=(1920, 1080))
c.eq("a rule that fits has nothing to scroll", short_panel._rule_scroll_max, 0)
c.true("...so it does not claim the wheel either",
       short_panel._rule_view is None
       or not short_panel.handle_rule_scroll(short_panel._rule_view.center, -1))

# A DIFFERENT rule opens at the top, rather than inheriting an offset measured
# against a longer one.
tall_panel.handle_rule_scroll(_view.center, -1)
# ALSO long, so a smaller scroll_max cannot zero the offset by itself -
# without that this check passes whether or not the reset exists.
tall_panel._draw_decision_rule(tall, tall_rect, 240, ("Some Other Rule", long_blocks))
c.eq("switching rules resets the scroll", tall_panel._rule_scroll, 0)


print()
print("3d) The ability's NAME is the heading, then the button, then the words")
# User, having been asked to pick a unit for Doom or Guide: "dann soll links
# bitte eine bessere einheitlichere Struktur sein. Erst als grosse ueberschrift
# der name der Ability. Dann der Knopf. Unter dem Knopf dann die Erklaerung."
_titles = []
_real_header = button_style.draw_panel_header


def _spy_header(surface, hrect, text, font, **kwargs):
    _titles.append((text, kwargs.get("wrap")))
    return _real_header(surface, hrect, text, font, **kwargs)


button_style.draw_panel_header = _spy_header
try:
    named_panel, named, named_rect = render(("Living Lightning", blocks))
    _named_titles, _titles[:] = list(_titles), []
    render(None)
    _plain_titles = list(_titles)
finally:
    button_style.draw_panel_header = _real_header
    _titles[:] = []

c.eq("the ability's own name is the heading", _named_titles[:1],
     [("LIVING LIGHTNING", True)])
# NOT a rare fallback: a good third of this game's board picks are core rules
# with no corpus entry at all, and there is no name to show for those.
c.eq("...and the generic title only where no rule resolved", _plain_titles[:1],
     [("CHOOSE A UNIT", True)])
# WRAPPED, because the title is a PRINTED name and nine of the corpus's 147
# ability titles are wider than this column's header bar - the widest,
# "Infused with the Blessings of Nurgle", by 76px.
LONG_NAME = "Infused with the Blessings of Nurgle"
c.true("the longest printed name really does not fit on one line",
       len(button_style.wrap_text(
           ActionPanel().header_font, LONG_NAME.upper(),
           config.LEFT_PANEL_WIDTH - 2 * button_style.HEADER_MARGIN
           - 2 * button_style.HEADER_TEXT_MARGIN)) > 1)
_long_panel, _long, _long_rect = render((LONG_NAME, blocks))


def first_button(panel):
    """The way out's rect, or None - so a probe that removes it turns this
    section RED instead of aborting the run on an IndexError."""
    return panel._buttons[0][0] if panel._buttons else None


c.true("...so the bar grows a line rather than running off the panel",
       first_button(_long_panel) is not None and first_button(named_panel) is not None
       and first_button(_long_panel).top > first_button(named_panel).top)
c.true("and no ink escapes the column while it does",
       all(_long.get_at((_long_rect.right + 2, y))[:3] == (0, 0, 0)
           for y in range(_long_rect.y + 2, _long_rect.y + 120, 2)))

# THE ORDER, measured off the drawn pixels rather than off the source. In the
# layout this replaces, the button was the LAST thing on the screen - under the
# prompt, the eligible list and the hint - so counting ink on either side of it
# is exactly what tells the two arrangements apart.
_button_rect = first_button(named_panel)
_title_bottom = named_rect.y + button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT
c.true("the way out is a button on this screen", _button_rect is not None)
c.true("the button is drawn under the heading",
       _button_rect is not None and _button_rect.top >= _title_bottom)
c.eq("...with nothing in between",
     [row for row in ink_below(named, named_rect, _title_bottom + 2)
      if _button_rect is not None and row < _button_rect.top - 1], [])
c.true("...and the explanation under the button",
       _button_rect is not None
       and bool(ink_below(named, named_rect, _button_rect.bottom + 4)))
c.true("the printed rule is the last thing on the screen",
       _button_rect is not None and (named_panel._rule_bottom or 0) > _button_rect.bottom)

# A rule that offers no way out gets no button - inventing an escape would
# change the rule - and the screen still reads heading, then explanation.
_no_exit = unit_pick_mod.UnitPick("Living Lightning - strike which unit?", None,
                                  [_pick_squad], {id(_pick_squad): 0}, [],
                                  lambda _i: None)
_mand_panel, _mand, _mand_rect = render_pick(_no_exit, ("Living Lightning", blocks))
c.eq("a mandatory choice draws no button", _mand_panel._buttons, [])
c.true("...and its explanation still sits under the heading",
       bool(ink_below(_mand, _mand_rect, _title_bottom + 2)))


print()
print("3e) The rule box is as tall as the rule, not as tall as the column")
# It used to run to the bottom edge unconditionally, so a one-paragraph rule
# sat under a mostly empty framed box - and an empty box reads as art that
# failed to load, the same reason nothing at all is drawn when there is no rule.
_one_panel, _one, _one_rect = render(("Living Lightning", blocks))
_two_panel, _two, _ = render(("Living Lightning", blocks * 2))
c.true("the box tracks the rule's own height",
       0 < (_one_panel._rule_bottom or 0) < (_two_panel._rule_bottom or 0))
c.true("...and a rule that fits stops short of the column's bottom",
       (_two_panel._rule_bottom or 0) < _one_rect.bottom)
_big_panel, _big, _big_rect = render(("Living Lightning", blocks * 12))
c.true("one that does not fit still uses all the room there is",
       _big_panel._rule_scroll_max > 0
       and (_big_panel._rule_bottom or 0) > (_two_panel._rule_bottom or 0))
c.true("...and stays inside the panel", (_big_panel._rule_bottom or 0) <= _big_rect.bottom)


# ---------------------------------------------------------------- 4) wiring
print()
print("4) main.py derives it for a board pick and passes it by keyword")
MAIN = open("main.py", encoding="utf-8").read()
c.true("the lookup runs", "prompt_rule.for_prompt(" in MAIN)
c.true("only for a board pick",
       "if frame_unit_pick is not None:" in MAIN)
c.true("it is handed to the LEFT panel by KEYWORD",
       "decision_rule=frame_decision_rule," in MAIN)
c.true("...and the right panel no longer takes it",
       "decision_rule=frame_decision_rule)" not in MAIN)
c.true("the right panel's own drawing is gone",
       "_draw_decision_rule" not in open("game/ui/game_status_panel.py", encoding="utf-8").read())
# The left panel's call site is positional for most of its length (error class
# 22 - this file carries the scar), so the new argument is a keyword.
c.true("the panel takes it on all three stages of the chain",
       open("game/ui/action_panel.py", encoding="utf-8").read().count("decision_rule=None,") == 2)
c.true("the wheel reaches it", "action_panel.handle_rule_scroll(mouse_pos, event.y)" in MAIN)
c.true("the deciding player is the one asked about, not whoever's turn it is",
       "_rule_owner = decision_manager.player" in MAIN)

c.finish()
