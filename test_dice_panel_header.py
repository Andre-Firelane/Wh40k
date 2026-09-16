"""The dice panel's HEADING: a big bold name for the roll, the target number,
and the modifiers with green up / red down arrows - plus the button row that
replaced "Click to confirm".

User: "Niemand liest lange Sätze mit zahlen drin im Spielgeschehen. Bei jedem
Roll muss groß und Fett drüber stehen was das für ein Wurf ist. Beispiel Roll
to Hit ... Rechts sollen Modifikationen schnell erkennbar angezeigt werden.
Positive Modifikatoren wie +1 (Ability XY) mit grünen Pfeil nach oben /
Darunter negative Modifikatoren wie -1 (Cover) mit rotem Pfeil nach unten."

Measured on a REAL DicePanel drawn onto a real surface, and on real roll sites
(ShootingController), not on the constants that produced the layout.

1. the name of a roll - explicit title, label fallback, kind fallback
2. modifiers in player terms - the sign is the whole point
3. what the real roll sites hand the panel
4. the heading on pixels
5. the button row
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

import testkit as tk  # noqa: E402
from testkit import Checks  # noqa: E402

from game import roll_choice  # noqa: E402
from game.dice import (DiceManager, HIT_ROLL, SAVE_ROLL, WOUND_ROLL, CHARGE_ROLL,  # noqa: E402
                       split_label, TITLE_BY_KIND)
from game.modifiers import Modifier, for_display  # noqa: E402
from game.factions.orks import FLASH_GITZ  # noqa: E402
from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402

c = Checks("dice panel heading + buttons")

pygame.init()
screen = pygame.display.set_mode((1280, 900))

from game.ui import dice_panel as dp  # noqa: E402


# ---------------------------------------------------------------------------
print("--- 1. the name of a roll ---")

c.eq("a label's name is what precedes ': '",
     split_label("Feel No Pain: Boy (2 wound(s))"), ("Feel No Pain", "Boy (2 wound(s))"))
c.eq("...else what precedes ' - '",
     split_label("Living Lightning - mortal wounds"), ("Living Lightning", "mortal wounds"))
c.eq("a parenthetical on the name is detail",
     split_label("Charge Roll (Heroic Intervention)"), ("Charge Roll", "Heroic Intervention"))
c.eq("a bracketed modifier list is dropped from the detail",
     split_label("Hit Roll: Rail rifle (3 attack(s)) [-1 (Target Uploaded)]"),
     ("Hit Roll", "Rail rifle (3 attack(s))"))
c.eq("keyword brackets around a name are typography",
     split_label("[SUSTAINED HITS 1]: Snazzgun (2 critical hit(s))")[0], "SUSTAINED HITS 1")
c.eq("no label, nothing", split_label(None), ("", ""))

dm = DiceManager()
dm.roll(count=3, label="Hit Roll: Rail rifle (3 attack(s))", title="Roll to Hit", subtitle="Rail rifle",
        roll_kind=HIT_ROLL)
c.eq("an explicit title wins", dm.display_title(), "Roll to Hit")
c.eq("...with its own subtitle", dm.display_subtitle(), "Rail rifle")
dm.roll(count=1, label="Deadly Demise: Battlewagon vs 2 Boyz 1")
c.eq("the next roll does not inherit the title", dm.display_title(), "Deadly Demise")
c.eq("...or the modifiers", dm.shown_modifiers, ())
dm.roll(count=2, roll_kind=CHARGE_ROLL)
c.eq("no title and no label falls back to the kind", dm.display_title(), TITLE_BY_KIND[CHARGE_ROLL])


# ---------------------------------------------------------------------------
print("--- 2. modifiers in player terms ---")

c.eq("cover worsens a hit threshold, so it is shown as -1",
     for_display([Modifier(1, "Benefit of Cover")]), ((-1, "Benefit of Cover"),))
c.eq("a threshold bonus is shown as +1",
     for_display([Modifier(-1, "Guided")]), ((1, "Guided"),))
c.eq("helpful ones come first, whatever order they were given in",
     for_display([Modifier(1, "Cover"), Modifier(-1, "Guided")]),
     ((1, "Guided"), (-1, "Cover")))
c.eq("a zero says nothing", for_display([Modifier(0, "Nothing")]), ())
c.eq("an additive roll's bonus is NOT negated",
     for_display([Modifier(2, "'Ere We Go")], lower_is_better=False), ((2, "'Ere We Go"),))
c.eq("(delta, source) pairs pass through in roll terms",
     for_display([(-2, "pinned"), (2, "'Ere We Go")]), ((2, "'Ere We Go"), (-2, "pinned")))


# ---------------------------------------------------------------------------
print("--- 3. what the real roll sites hand the panel ---")

tk.script(default=6)
scene = tk.shooting_scene(FLASH_GITZ, STRIKE_TEAM, gap=10.0)
sc, dice = scene["shooting"], scene["dice"]
sc.start_shooting(scene["attacker"])
sc.choose_target_squad(scene["target"])
key = next(k for k, *rest in sc.weapon_eligibility() if "Snazzgun" in str(rest[0]))
# The Dakka profile (AP-1): the Snazzgun's first profile, the Cutta, is AP-3 and
# makes the Strike Team's 4+ save an impossible 7+, which this engine does not
# roll at all - so there would be no save roll to title.
sc.choose_weapon(key, profile=1)
c.eq("the hit roll is pending", sc.pending_step, "hit")
c.eq("the hit roll is titled", dice.title, "Roll to Hit")
c.eq("...its subtitle is the weapon, not a sentence",
     dice.subtitle, sc.current_group["weapon_label"])
c.eq("...and it carries the same modifiers the threshold was built from",
     dice.shown_modifiers, for_display(sc._hit_modifiers(sc.current_group)))
c.true("the LOG label is unchanged - it is still the sentence the tests pin",
       dice.label.startswith("Hit Roll: "))
for _ in range(6):
    if sc.pending_step == "wound" or not dice.is_pending:
        break
    dice.acknowledge()
    sc.on_dice_acknowledged()
c.eq("the wound roll is titled", dice.title if sc.pending_step == "wound" else None, "Roll to Wound")
for _ in range(6):
    if sc.pending_step == "save" or not dice.is_pending:
        break
    dice.acknowledge()
    sc.on_dice_acknowledged()
c.eq("the save roll is titled", dice.title if sc.pending_step == "save" else None, "Roll to Save")


# ---------------------------------------------------------------------------
print("--- 4. the heading on pixels ---")


class SpyFont:
    """A font that remembers every string it rendered - pygame's Font render
    attribute cannot be patched on the instance."""

    def __init__(self, font, sink):
        self._font = font
        self._sink = sink

    def render(self, text, *args, **kwargs):
        self._sink.append(text)
        return self._font.render(text, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._font, name)


BOARD = pygame.Rect(220, 40, 840, 820)


def shown(dm, choice=None, selecting=False, actions=(), hint=None):
    """A real panel, driven through slide-in and tumble to SHOWN, then drawn
    onto a clean surface. Returns (panel, surface, rendered strings by font)."""
    panel = dp.DicePanel()
    rendered = {}
    for name in ("title_font", "subtitle_font", "threshold_font", "modifier_font",
                 "hint_font", "label_font", "button_font", "matchup_font", "crit_font"):
        rendered[name] = []
        setattr(panel, name, SpyFont(getattr(panel, name), rendered[name]))
    surf = pygame.Surface((1280, 900))
    board = BOARD
    panel.draw(surf, dm, bounds_rect=board, choice=choice, actions=actions)
    panel._anim_start -= 10
    panel._flicker_start -= 10
    panel.draw(surf, dm, bounds_rect=board, choice=choice, actions=actions)
    panel._anim_start -= 10
    for sink in rendered.values():
        sink.clear()
    surf.fill((0, 0, 0))
    panel.draw(surf, dm, bounds_rect=board, choice=choice, selecting_die=selecting,
               actions=actions, selecting_hint=hint)
    return panel, surf, rendered


def pixels_of(surf, rect, color):
    out = []
    for y in range(rect.top, rect.bottom):
        for x in range(rect.left, rect.right):
            if tuple(surf.get_at((x, y)))[:3] == color:
                out.append((x, y))
    return out


LABEL = "Hit Roll: Avenger Shuriken Catapult (8 attack(s)) [+1 (Benefit of Cover), -1 (Guided)]"
hit = DiceManager()
tk.script(1, 2, 3, 4, 5, 6, 6, 5)
hit.roll(count=8, label=LABEL, title="Roll to Hit", subtitle="Avenger Shuriken Catapult",
         shown_modifiers=for_display([Modifier(1, "Benefit of Cover"), Modifier(-1, "Guided")]),
         success_threshold=4, roll_kind=HIT_ROLL, target_name="2 Boyz 1")
panel, surf, rendered = shown(hit)
c.true("the panel reached its revealed state", panel.last_backdrop_rect is not None)
c.eq("the title is set in capitals with the title font", rendered["title_font"], ["ROLL TO HIT"])
c.eq("the weapon is the subtitle", rendered["subtitle_font"], ["Avenger Shuriken Catapult"])
c.eq("the target number is drawn big", rendered["threshold_font"], ["4+"])
c.eq("each modifier is one row, helpful first",
     rendered["modifier_font"], ["+1 (Guided)", "-1 (Benefit of Cover)"])
all_text = [t for sink in rendered.values() for t in sink]
c.eq("the label SENTENCE is never drawn", [t for t in all_text if "attack(s)" in t], [])
c.true("the title font is taller than the subtitle font",
       panel.title_font.get_height() > panel.subtitle_font.get_height())
c.true("...and bold", panel.title_font.get_bold())

box = panel.last_backdrop_rect
green = pixels_of(surf, box, dp.POSITIVE_MODIFIER_COLOR)
red = pixels_of(surf, box, dp.NEGATIVE_MODIFIER_COLOR)
c.true("green is drawn", len(green) > 20)
c.true("red is drawn", len(red) > 20)
c.true("the green row sits ABOVE the red one",
       green and red and max(y for _x, y in green) < min(y for _x, y in red))
c.true("the modifiers are on the RIGHT half of the panel",
       green and red and min(x for x, _y in green + red) > box.centerx)


def arrow_points_up(points):
    """A filled triangle is widest at its base: pointing up, the widest row is
    its lowest."""
    if not points:
        return None
    ys = sorted({y for _x, y in points})
    rows = {y: [x for x, yy in points if yy == y] for y in ys}
    # the arrow is the left-most blob of this colour - text follows it
    left = min(x for x, _y in points)
    widths = {y: len([x for x in xs if x < left + dp.MODIFIER_ARROW_W + 1]) for y, xs in rows.items()}
    widths = {y: w for y, w in widths.items() if w}
    top, bottom = min(widths), max(widths)
    return widths[bottom] > widths[top]


c.eq("the green arrow points UP", arrow_points_up(green), True)
c.eq("the red arrow points DOWN", arrow_points_up(red), False)

# Colour must not carry the meaning alone: the SIGN is in the text as well.
c.true("the sign is printed on both rows",
       rendered["modifier_font"][0].startswith("+") and rendered["modifier_font"][1].startswith("-"))

plain = DiceManager()
plain.roll(count=3, label="Living Lightning - mortal wounds")
p2, s2, r2 = shown(plain)
c.eq("a roll with no title is named from its label", r2["title_font"], ["LIVING LIGHTNING"])
c.eq("...and has no target-number box when it has no threshold and no modifier",
     r2["threshold_font"] + r2["modifier_font"], [])

save = DiceManager()
tk.script(1, 2, 6)
save.roll(count=3, label="Save Roll: Bolter (3 wound(s))", title="Roll to Save", subtitle="Bolter",
          shown_modifiers=((-2, "AP"),), success_threshold=5, roll_kind=SAVE_ROLL, damage_per_failure=2)
p3, s3, r3 = shown(save)
c.eq("AP is shown as a harmful modifier", r3["modifier_font"], ["-2 (AP)"])
summary = [t for t in r3["label_font"]]
c.eq("the save summary is short", summary, ["2 UNSAVED - 2 DAMAGE EACH"])
c.eq("...and the old sentence is gone",
     [t for sink in r3.values() for t in sink if "get through" in t], [])


# ---------------------------------------------------------------------------
print("--- 5. the button row ---")

c.eq("with nothing on offer the row is a lone Accept",
     [o.key for o, _r in panel._button_rects], [roll_choice.ACCEPT])
c.eq("\"Click to confirm\" is gone", [t for t in all_text if "Click to confirm" in t], [])

choice = roll_choice.RollChoice("Player 1", [
    roll_choice.RollOption(roll_choice.WHOLE, 8),
    roll_choice.RollOption(roll_choice.ACCEPT),
    roll_choice.RollOption(roll_choice.FAILURES, 4),
])
p4, s4, r4 = shown(hit, choice=choice)
keys = [o.key for o, _r in p4._button_rects]
c.eq("every offered option is a button, Accept first", keys,
     [roll_choice.ACCEPT, roll_choice.FAILURES, roll_choice.WHOLE])
c.eq("the buttons say how many dice", [o.label for o, _r in p4._button_rects],
     ["Accept", "Re-roll failures (4)", "Re-roll all (8)"])
rects = [r for _o, r in p4._button_rects]
c.true("every button lies inside the panel",
       all(p4.last_backdrop_rect.contains(r) for r in rects))
c.true("no two buttons overlap",
       all(not a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:]))
# Guarded so a panel that draws NO buttons reddens these lines instead of
# crashing the suite on an empty min() / rects[1] (a probe that removes the row
# found that).
c.true("the buttons sit BELOW the dice",
       bool(rects) and bool(p4._die_rects)
       and min(r.top for r in rects) > max(r.bottom for _i, r in p4._die_rects))
c.eq("button_at() answers the button under the cursor",
     getattr(p4.button_at(rects[1].center), "key", None) if len(rects) > 1 else None,
     roll_choice.FAILURES)
c.true("...and nothing between them",
       bool(rects) and p4.button_at((rects[0].right + 1, rects[0].centery)) is None)

mandatory = roll_choice.RollChoice("Player 1", [
    roll_choice.RollOption(roll_choice.FAILURES, 4),
    roll_choice.RollOption(roll_choice.ONES, 1),
    roll_choice.RollOption(roll_choice.WHOLE, 8),
])
p5, _s5, _r5 = shown(hit, choice=mandatory)
c.eq("no Accept when keeping the result is not legal",
     [o.key for o, _r in p5._button_rects if o.key == roll_choice.ACCEPT], [])
c.eq("...which the choice says too", mandatory.accept_allowed, False)

p6, _s6, r6 = shown(hit, choice=choice, selecting=True)
c.eq("while picking a die the buttons stand aside", p6._button_rects, [])
c.true("...for the pick hint", "Click a die to re-roll it." in r6["hint_font"])

narrow = pygame.Rect(300, 40, 360, 820)
p7 = dp.DicePanel()
s7 = pygame.Surface((1280, 900))
p7.draw(s7, hit, bounds_rect=narrow, choice=choice)
p7._anim_start -= 10
p7._flicker_start -= 10
p7.draw(s7, hit, bounds_rect=narrow, choice=choice)
p7._anim_start -= 10
p7.draw(s7, hit, bounds_rect=narrow, choice=choice)
r7 = [r for _o, r in p7._button_rects]
c.true("on a narrow board the row wraps instead of leaving the panel",
       len({r.top for r in r7}) > 1 and all(p7.last_backdrop_rect.contains(r) for r in r7))


# ---------------------------------------------------------------------------
print("--- 6. the Stratagem and ability buttons ---")
# User: "buttons für fähigkeiten und stratagems sollen doch mit in das würfel
# panel rein, statt links in die spalte." Command Re-roll, Targeting Array and
# the unmodified-6 abilities used to be the left panel's pending-roll screen.

pressed = []
abilities = [
    roll_choice.RollOption(roll_choice.COMMAND_REROLL, label="Command Re-roll (1 CP)", acknowledges=False,
                           apply=lambda: pressed.append("command"), accent="stratagem"),
    roll_choice.RollOption(roll_choice.UNMODIFIED_SIX, label="Aspect Shrine token (1 token left)",
                           acknowledges=False, apply=lambda: pressed.append("six")),
]
_accents = []
_real_draw_button = dp.button_style.draw_button


def _spy_draw_button(surface, rect, label, font, **kwargs):
    _accents.append((label, kwargs.get("accent")))
    return _real_draw_button(surface, rect, label, font, **kwargs)


dp.button_style.draw_button = _spy_draw_button
try:
    p8, _s8, _r8 = shown(hit, choice=choice, actions=abilities)
finally:
    dp.button_style.draw_button = _real_draw_button
roll_rects = [r for _o, r in p8._button_rects]
ability_rects = [r for _o, r in p8._action_rects]
c.eq("every Stratagem/ability button is drawn ON THE DICE PANEL",
     [o.label for o, _r in p8._action_rects], ["Command Re-roll (1 CP)", "Aspect Shrine token (1 token left)"])
c.true("...inside it", bool(ability_rects) and all(p8.last_backdrop_rect.contains(r) for r in ability_rects))
c.true("...on a row BELOW the roll's own buttons, which stay first",
       bool(roll_rects) and bool(ability_rects)
       and min(r.top for r in ability_rects) > max(r.bottom for r in roll_rects))
c.true("...overlapping none of them",
       all(not a.colliderect(b) for a in ability_rects for b in roll_rects))
c.eq("action_at() answers an ability button",
     getattr(p8.action_at(ability_rects[0].center), "key", None) if ability_rects else None,
     roll_choice.COMMAND_REROLL)
c.eq("...and button_at() does not - the roll's own list stays the roll's (click-anywhere reads it)",
     p8.button_at(ability_rects[0].center) if ability_rects else "no button drawn", None)
_accent_of = dict(_accents)
c.eq("a Command Re-roll button says what it costs: the Stratagem accent",
     _accent_of.get("Command Re-roll (1 CP)"), "stratagem")
c.eq("...Accept stays the confirm accent", _accent_of.get("Accept"), "confirm")

cancel = [roll_choice.RollOption(roll_choice.CANCEL, label="Cancel", acknowledges=False,
                                 apply=lambda: pressed.append("cancel"), accent="danger")]
p9, _s9, r9 = shown(hit, choice=choice, selecting=True, actions=cancel, hint=roll_choice.UNMODIFIED_SIX_PICK_HINT)
c.eq("while a die is picked the roll's buttons stand aside", p9._button_rects, [])
c.eq("...for the pick's Cancel", [o.key for o, _r in p9._action_rects], [roll_choice.CANCEL])
c.true("...under the hint the pick hands over", roll_choice.UNMODIFIED_SIX_PICK_HINT in r9["hint_font"])

big = DiceManager()
tk.script(default=3)
big.roll(count=40, label="Hit Roll: Shoota (40 attack(s))", title="Roll to Hit", subtitle="Shoota",
         success_threshold=4, roll_kind=HIT_ROLL, target_name="2 Boyz 1")
p10, _s10, _r10 = shown(big, choice=choice, actions=abilities + abilities)
c.true("a 40-dice roll with two rows of ability buttons still stays on the board",
       p10.last_backdrop_rect is not None and BOARD.contains(p10.last_backdrop_rect))
c.true("...and draws all four", len(p10._action_rects) == 4)

c.finish()
