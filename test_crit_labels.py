"""[LETHAL HITS] without a prompt, and what a critical die is labelled with.

User: "bei lethal hits kommt gerade ein seltsames overlay, in dem ich eine
liste bekomme, wieviele hits automatisch verwunden sollen. das koennen wir
uns sparen. es sollen einfach alle kritischen treffer automatisch verwunden."

User: "zusaetzlich markiere bitte die kritischen gewuerfelten treffer mit
'lethal hit', wenn diese Regel aktiv ist. Gleiches gilt fuer 'sustained hit'
oder 'devastating wound'."

Two claims:

  1. rule 24.23 is taken for every critical hit, with no DecisionManager
     prompt - measured as "the critical hits do not reach the wound roll",
     which is what the rule actually does.
  2. a roll carries the critical threshold of THIS roll plus what a critical
     die on it buys, and the panel prints that under exactly those dice.

The labels are the interesting half to test, because almost every keyword
involved is a CONDITIONAL grant applied at resolution time - so the note has
to be taken from the adjusted weapon, not the printed one. The Ammo Runt is
the A/B for that: the same Flash Gitz, the same all-sixes hit roll, with and
without the grant.

Real controllers and a real headless render throughout.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

from game.dice import DiceManager, HIT_ROLL
from game.factions.aeldari import HOWLING_BANSHEES
from game.factions.orks import BEAST_SNAGGA_BOYZ, BOYZ, FLASH_GITZ
from game.factions.tau_empire import (
    PATHFINDER_CARBINE_TO_RAIL_RIFLE, PATHFINDER_TEAM, STRIKE_TEAM,
)

c = Checks("lethal hits + critical dice labels")

pygame.init()
screen = pygame.display.set_mode((960, 700))

from game.ui import dice_panel as dp          # noqa: E402  (needs a display)
from game.ui.dice_panel import DicePanel      # noqa: E402


# ---------------------------------------------------------------------------
# 1. [LETHAL HITS] is taken for every critical hit, without asking
# ---------------------------------------------------------------------------

print("--- 1. lethal hits ---")


def snazzguns(ammo_runt):
    """One Flash Gitz activation, every hit roll a natural 6 - so every hit
    is critical and rule 24.23 (when the Ammo Runt grants it) applies to all
    of them. Stopped right after the hit roll resolves, which is where the
    wound roll is pending and its dice countable."""
    tk.script(*([6] * 60))
    scene = tk.shooting_scene(FLASH_GITZ, STRIKE_TEAM, gap=10.0)
    scene["attacker"].ammo_runt_active = ammo_runt
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    sc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in sc.weapon_eligibility() if "Snazzgun" in str(rest[0]))
    sc.choose_weapon(key)
    hit_note = (scene["dice"].crit_threshold, scene["dice"].crit_labels)
    scene["dice"].acknowledge()
    sc.on_dice_acknowledged()
    return scene, hit_note


with_runt, runt_hit_note = snazzguns(True)
without, plain_hit_note = snazzguns(False)

c.eq("[LETHAL HITS] no longer interrupts the activation with a prompt",
     with_runt["decision"].is_pending, False)
c.true("both runs reached the wound step",
       len(without["dice"].pending_values or []) > 0)
c.true("with the keyword the critical hits auto-wound instead of rolling",
       len(with_runt["dice"].pending_values) < len(without["dice"].pending_values))
# Every hit is critical here, and [SUSTAINED HITS] doubles the hit count -
# so exactly half of the hits are the crits that skip the wound roll.
c.eq("exactly the critical hits skip it",
     len(with_runt["dice"].pending_values) * 2, len(without["dice"].pending_values))


# ---------------------------------------------------------------------------
# 2. the labels, and the threshold they are keyed on
# ---------------------------------------------------------------------------

print("--- 2. labels ---")

c.eq("a granted [LETHAL HITS] shows up on the hit dice",
     runt_hit_note[1], ("LETHAL HIT", "SUSTAINED HIT"))
c.eq("A/B: without the grant only the printed keyword does",
     plain_hit_note[1], ("SUSTAINED HIT",))
c.eq("rule 05.02's default critical threshold", runt_hit_note[0], 6)
c.eq("a wound roll with no such keyword is left unlabelled",
     with_runt["dice"].crit_labels, ())


def rail_rifles():
    """[DEVASTATING WOUNDS] is a WOUND-roll keyword (24.10), so it has to be
    read at that step and not at the hit step."""
    tk.script(*([6] * 60))
    scene = tk.shooting_scene(
        PATHFINDER_TEAM, BOYZ, attacker_owner="Player 1", gap=10.0,
        attacker_choices={"Pathfinder": {PATHFINDER_CARBINE_TO_RAIL_RIFLE: 3}},
    )
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    if sc.state == "choosing_shooting_type":
        sc.choose_shooting_type(sc.available_types[0])
    sc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in sc.weapon_eligibility() if "Rail" in str(rest[0]))
    sc.choose_weapon(key)
    hit_labels = scene["dice"].crit_labels
    scene["dice"].acknowledge()
    sc.on_dice_acknowledged()
    return hit_labels, scene["dice"].crit_labels


rail_hit, rail_wound = rail_rifles()
c.eq("[DEVASTATING WOUNDS] is not a hit-roll label", rail_hit, ())
c.eq("...it labels the wound dice", rail_wound, ("DEVASTATING WOUND",))


def banshees():
    """[ANTI-INFANTRY 3+] (24.03) lowers the WOUND roll's critical threshold,
    so the panel has to mark the right dice rather than just the sixes."""
    tk.script(*([6] * 60))
    scene = tk.fight_scene(HOWLING_BANSHEES, BOYZ, attacker_owner="Player 1")
    fc = scene["fight"]
    fc.select_to_fight(scene["attacker"])
    if fc.target_squad is None:
        fc.choose_target_squad(scene["target"])
    if fc.current_group is None:
        fc.choose_weapon(fc.weapon_eligibility()[0][0])
    scene["dice"].acknowledge()
    fc.on_dice_acknowledged()
    return scene["dice"].crit_threshold


c.eq("[ANTI-INFANTRY 3+] lowers the critical threshold on the wound roll",
     banshees(), 3)


def melee_note():
    """The fight phase has its own adjuster chain (Get Stuck In, Spirit of
    Gork), so its labels are wired separately and tested separately."""
    tk.script(*([6] * 40))
    scene = tk.fight_scene(BEAST_SNAGGA_BOYZ, BOYZ)
    scene["attacker"].spirit_of_gork_lethal = True
    fc = scene["fight"]
    fc.select_to_fight(scene["attacker"])
    if fc.target_squad is None:
        fc.choose_target_squad(scene["target"])
    if fc.current_group is None:
        fc.choose_weapon(next(k for k, *r in fc.weapon_eligibility() if "Choppa" in str(r[0])))
    return scene["dice"].crit_labels


c.eq("the fight phase labels its crits the same way",
     melee_note(), ("LETHAL HIT", "SUSTAINED HIT"))

# is_critical() itself - rules 05.01/05.02's floor, the same one is_success()
# applies for the same reason.
probe = DiceManager()
probe.roll(count=1, sides=6, label="x", crit_threshold=3)
c.true("a die at the threshold is critical", probe.is_critical(3))
c.true("...and above it", probe.is_critical(6))
c.true("below it is not", not probe.is_critical(2))
c.true("an unmodified 1 is never critical, however low the threshold",
       not probe.is_critical(1))
probe.roll(count=1, sides=6, label="x")
c.true("a roll with no critical notion at all says no", not probe.is_critical(6))


# ---------------------------------------------------------------------------
# 3. the panel prints them under exactly the critical dice
# ---------------------------------------------------------------------------

print("--- 3. the panel prints them ---")

rows = []
real_row = DicePanel._draw_dice_row


def row_spy(self, ops, movable, surf, row, y, dm, selecting, pl, pw, entrance_elapsed=None,
            gap=None):
    before = len(movable)
    out = real_row(self, ops, movable, surf, row, y, dm, selecting, pl, pw,
                   entrance_elapsed=entrance_elapsed, gap=gap)
    rows.append((len(movable) - before, out - y))
    return out


def dice_row(labels, values, reveal=True):
    """Renders one roll and returns [(rects made, row height)] per dice row.
    Every rect a row makes is either a die or one line of a crit label, so
    counting them is what says whether the labels were drawn."""
    dice = DiceManager()
    dice.roll(count=len(values), sides=6, label="Hit Roll: x", success_threshold=4,
              roll_kind=HIT_ROLL, target_name="B", crit_threshold=6, crit_labels=labels)
    dice.pending_values[:] = values
    dice.last_values = dice.pending_values
    panel = DicePanel()
    bounds = pygame.Rect(0, 0, 960, 700)
    for _ in range(400):
        screen.fill((25, 28, 32))
        panel.draw(screen, dice, bounds_rect=bounds)
        if panel._phase == dp.SHOWN or not reveal:
            break
        panel._anim_start = -1e9      # skip the wall-clock wait
        panel._flicker_start = -1e9
    rows.clear()
    DicePanel._draw_dice_row = row_spy
    screen.fill((25, 28, 32))
    panel.draw(screen, dice, bounds_rect=bounds)
    DicePanel._draw_dice_row = real_row
    return list(rows)


values = [6, 6, 4, 2]          # two critical dice, two ordinary ones
plain_rows = dice_row((), values)
labelled = dice_row(("LETHAL HIT",), values)
two_words = dice_row(("DEVASTATING WOUND",), values)

c.true("the row is drawn at all", len(plain_rows) >= 1)
c.eq("without labels a row makes one rect per die",
     sum(n for n, _h in plain_rows), len(values))
c.eq("with a label the two critical dice each get one more rect",
     sum(n for n, _h in labelled) - sum(n for n, _h in plain_rows), 2)
c.true("...and the row grows taller to fit it",
       max(h for _n, h in labelled) > max(h for _n, h in plain_rows))
# ONE rect per labelled die however many lines the label needs: the label is
# drawn as a single filled BADGE now (user: "die Labels für crits bei lethal
# oder sustained gerne etwas auffälliger"), and a two-line label is one plate
# rather than two stacked ones - two would read as two separate things being
# said about the same die.
c.eq("a longer label is still ONE badge per critical die",
     sum(n for n, _h in two_words) - sum(n for n, _h in plain_rows), 2)
# A label that REALLY wraps. Every printed one fits on a line at this width,
# so the two-line case has to be constructed - without it "one badge, however
# many lines" is never actually exercised, and an A/B that put one plate per
# line back stayed green.
_wrapped = dice_row(("SUSTAINED HIT AND DEVASTATING WOUND",), values)
_panel_for_wrap = DicePanel()
c.true("the fixture really does wrap to more than one line",
       len(_panel_for_wrap._crit_label_texts(("SUSTAINED HIT AND DEVASTATING WOUND",))) > 1)
c.eq("...and it is STILL one badge per die, not one per line",
     sum(n for n, _h in _wrapped) - sum(n for n, _h in plain_rows), 2)
c.true("...but a taller one",
       max(h for _n, h in _wrapped) > max(h for _n, h in labelled))

mid_tumble = dice_row(("LETHAL HIT",), values, reveal=False)
c.eq("nothing is labelled while the dice are still tumbling",
     sum(n for n, _h in mid_tumble), len(values))


# ---------------------------------------------------------------------------
# 4. the panel HOLDS them - the reported overflow
# ---------------------------------------------------------------------------
print("--- 4. nothing escapes the panel ---")

# User: "die würfel fliegen optisch aus dem würfelpanel wenn es zu viele
# werden. die größe des würfelpanels muss sich anpassen."
#
# The cause was one number worked out twice: draw() counted dice per row at
# DICE_GAP while _draw_dice_row() laid them out at the wider crit-label
# spacing. Ten dice then measured 734px inside a 640px panel and hung 47px off
# EACH side. Measured against the panel's OWN backdrop, so this asks where it
# actually put things rather than re-deriving the layout.


def settled(n, labels=(), bounds=None):
    """A finished roll of `n` sixes, drawn twice - the crit layout is withheld
    while the dice tumble, so the overflow only exists once revealed."""
    bounds = bounds or pygame.Rect(220, 0, 1480, 700)
    dice = DiceManager()
    dice.roll(count=n, sides=6, label="Gauss Flayer Array hit roll",
              success_threshold=3, roll_kind=HIT_ROLL, target_name="B",
              crit_threshold=6 if labels else None, crit_labels=labels)
    dice.pending_values[:] = [6] * n
    dice.last_values = dice.pending_values
    panel = DicePanel()
    surface = pygame.Surface((bounds.right + 40, bounds.bottom + 100))
    panel.draw(surface, dice, bounds_rect=bounds)
    panel._phase = dp.SHOWN
    panel.draw(surface, dice, bounds_rect=bounds)
    return panel, bounds


def outside(panel):
    """How far the widest die sticks out of the backdrop, in pixels."""
    back = panel.last_backdrop_rect
    if back is None or not panel._die_rects:
        return None
    left = min(r.left for _i, r in panel._die_rects)
    right = max(r.right for _i, r in panel._die_rects)
    return max(0, back.left - left, right - back.right)


for count in (6, 10, 20, 30, 40):
    panel, _b = settled(count)
    c.eq(f"{count} plain dice stay inside the panel", outside(panel), 0)
    panel, _b = settled(count, ("LETHAL HIT",))
    c.eq(f"{count} dice WITH a crit label stay inside the panel", outside(panel), 0)
    panel, _b = settled(count, ("DEVASTATING WOUND",))
    c.eq(f"{count} dice with a LONG crit label stay inside", outside(panel), 0)

# The row length and the spacing are ONE decision now. Asked of the panel
# directly, because that is the disagreement that put the dice outside.
_panel = DicePanel()
_dm = DiceManager()
_dm.crit_threshold, _dm.crit_labels = 6, ("SUSTAINED HIT",)
_plain_gap = _panel._row_gap(_dm, revealed=False)
_crit_gap = _panel._row_gap(_dm, revealed=True)
c.eq("while the dice tumble the spacing gives nothing away", _plain_gap, dp.DICE_GAP)
c.true("...and a revealed crit label widens the row", _crit_gap > _plain_gap)
# DERIVED from the badge, not a constant: the label is as wide as its words.
c.true("the gap leaves real air between two badges",
       _crit_gap >= _panel._crit_badge_width(_dm.crit_labels) - dp.DICE_SIZE)
_long = DiceManager()
_long.crit_threshold, _long.crit_labels = 6, ("DEVASTATING WOUND",)
c.true("a longer label opens a wider gap",
       _panel._row_gap(_long, revealed=True) > _crit_gap)

# The PANEL grows when the dice would not otherwise fit the board area. The
# preferred width is a user decision ("das panel sollte vielleicht nicht über
# die gesamte breite gehen"), so an ordinary roll must not move it.
_narrow = pygame.Rect(220, 0, 1480, 700)
_small, _b = settled(12, ("LETHAL HIT",), _narrow)
c.eq("an ordinary roll keeps the preferred width",
     _small.last_backdrop_rect.width, dp.MAX_PANEL_WIDTH)
_big, _b = settled(80, ("LETHAL HIT",), _narrow)
c.true("...and a huge roll widens the panel instead of running off the bottom",
       _big.last_backdrop_rect.width > dp.MAX_PANEL_WIDTH)
c.true("...without leaving the board area",
       _big.last_backdrop_rect.bottom <= _narrow.bottom
       and _narrow.contains(_big.last_backdrop_rect))
c.eq("...and still with every die inside it", outside(_big), 0)


# ---------------------------------------------------------------------------
# 5. the labels are LOUD
# ---------------------------------------------------------------------------
print("--- 5. the badge ---")

# User: "außerdem hätte ich die Labels für crits bei lethal oder sustained
# gerne etwas auffälliger." Measured on PIXELS: a check that only asked whether
# the text was drawn would pass on the quiet version this replaces.

GROUND = (25, 28, 32)


def label_band(labels):
    """Every colour in the strip just under the first row of dice."""
    dice = DiceManager()
    dice.roll(count=4, sides=6, label="Hit Roll", success_threshold=3,
              roll_kind=HIT_ROLL, target_name="B", crit_threshold=6,
              crit_labels=labels)
    dice.pending_values[:] = [6, 6, 4, 2]
    dice.last_values = dice.pending_values
    panel = DicePanel()
    bounds = pygame.Rect(0, 0, 960, 700)
    surface = pygame.Surface((1000, 800))
    surface.fill(GROUND)
    panel.draw(surface, dice, bounds_rect=bounds)
    panel._phase = dp.SHOWN
    surface.fill(GROUND)
    panel.draw(surface, dice, bounds_rect=bounds)
    # The WHOLE panel, not a band under one die: the dice are regrouped into
    # success/failure blocks once revealed, so "the first die" is not
    # necessarily a critical one and a narrow band can miss every badge.
    back = panel.last_backdrop_rect
    seen = {}
    for y in range(back.top, back.bottom):
        for x in range(back.left, back.right):
            colour = surface.get_at((x, y))[:3]
            seen[colour] = seen.get(colour, 0) + 1
    return seen


band = label_band(("LETHAL HIT",))
c.true("the badge is FILLED, not loose text",
       band.get(dp.CRIT_LABEL_BG_COLOR, 0) > 200)
c.true("...with its text dark on top of it",
       any(sum(colour) < 200 for colour in band))
c.true("...and a lighter edge around it", dp.CRIT_LABEL_BORDER_COLOR in band)
# The fill has to out-shout the panel it sits on, or none of the above helps.
_contrast = sum(abs(dp.CRIT_LABEL_BG_COLOR[i] - dp.BACKDROP_COLOR[i]) for i in range(3)) / 3
c.true("the badge stands well clear of the panel behind it", _contrast > 120)
c.true("...and its text stands clear of the badge",
       sum(abs(dp.CRIT_LABEL_BG_COLOR[i] - dp.CRIT_LABEL_COLOR[i]) for i in range(3)) / 3 > 120)

plain = label_band(())
c.eq("an ordinary die gets no badge at all", plain.get(dp.CRIT_LABEL_BG_COLOR, 0), 0)

c.finish()
