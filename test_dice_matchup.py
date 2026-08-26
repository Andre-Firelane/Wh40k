"""The dice panel's "who is attacking whom" line, and the sprite order
behind it.

User: "wenn du beim wuerfel panel anzeigst, was auf wen schiesst, baue bitte
die sprites mit ein, damit man es besser auf den ersten blick erkennen kann."

User, on the thumbnails themselves: "wenn du 2 sprites anzeigen laesst zb bei
der pre game phase, wenn angeschlossene charaktere in squads sind, dann zeige
immer zuerst den charakter an und danach den squad ... dort soll der der
teurste charakter angezeigt werden (farseer) und dann der squad (defenders)".

Three claims, tested separately because they can fail independently:

  1. sprites.portrait_paths() leads an attached unit (19.01) with ONE
     character - the most expensive one - and then the rank and file.
  2. every roll of an attack sequence carries both units, so the panel has
     something to draw.
  3. the panel actually draws it, inside its own width, at every window size.
  4. a roll that names a unit which is NOT a target (a Charge roll names the
     unit doing the charging) shows that unit's art, and says what it is.

Real engine objects throughout (a real ShootingController/FightController
activation driven to the end, a real headless render of the panel), and the
first and third claims carry an A/B against the pre-change behaviour: "it
passes now" says nothing on its own about whether the check would have
caught the report.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

from game import attached_units, sprites
from game.dice import DiceManager, HIT_ROLL, SAVE_ROLL
from game.factions.aeldari import (
    FARSEER, GUARDIAN_DEFENDERS, STORM_GUARDIANS, STRIKING_SCORPIONS, WARLOCK_CONCLAVE,
)
from game.factions.orks import BOYZ, GRETCHIN, WARBOSS

c = Checks("dice panel matchup + portrait order")

pygame.init()
pygame.display.set_mode((1400, 700))

from game.ui import dice_panel as dp          # noqa: E402  (needs a display)
from game.ui.dice_panel import DicePanel      # noqa: E402


def base(paths):
    return [os.path.basename(p) for p in paths]


# ---------------------------------------------------------------------------
# 1. portrait_paths(): character first, then the squad
# ---------------------------------------------------------------------------

print("--- 1. portrait order ---")

guardians = tk.build(GUARDIAN_DEFENDERS, "Player 1", name="Guardian Defenders 1")
farseer = tk.build(FARSEER, "Player 1", name="Farseer")
conclave = tk.build(WARLOCK_CONCLAVE, "Player 1", name="Warlock Conclave 1")

# The scene is asserted before it is used: the rule is "most EXPENSIVE
# character", so a test whose Farseer happened to be the cheaper one would
# pass while proving the opposite.
c.true("the Farseer is the dearer of the two characters",
       farseer.points > conclave.points)

merged = attached_units.attach(conclave, attached_units.attach(farseer, guardians))
c.eq("three components (19.01)", len(attached_units.components(merged)), 3)

c.eq("two thumbnails: the dearest character, then the rank and file",
     base(sprites.portrait_paths(merged, 2)),
     ["Farseer.png", "Guardian Defender.png"])
c.eq("one thumbnail is the character",
     base(sprites.portrait_paths(merged, 1)), ["Farseer.png"])
c.eq("the platform and the second character come after that",
     base(sprites.portrait_paths(merged, 4)),
     ["Farseer.png", "Guardian Defender.png",
      "Bright Lance Weapon Platform.png", "Warlock Conclaive.png"])

# The rank-and-file half is a rule of its own: a datasheet lists its single
# support model FIRST, so without it the second slot goes to the platform.
plain = tk.build(GUARDIAN_DEFENDERS, "Player 1", name="Guardian Defenders 2")
c.eq("a plain squad leads with its most numerous line, not its platform",
     base(sprites.portrait_paths(plain, 2)),
     ["Guardian Defender.png", "Bright Lance Weapon Platform.png"])
c.eq("...same for Storm Guardians",
     base(sprites.portrait_paths(
         tk.build(STORM_GUARDIANS, "Player 1", name="Storm Guardians 1"), 2)),
     ["Assault Guardian.png", "Bright Lance Weapon Platform.png"])

# A/B: the pre-change order was plain Squad.models order - bodyguards first,
# character cut off entirely, which is what the report is about.
pre_order = base(dict.fromkeys(
    p for p in (sprites.sprite_for(m) for m in merged.models) if p is not None))
c.eq("PRE-CHANGE (plain model order) led with the squad",
     pre_order[:2], ["Bright Lance Weapon Platform.png", "Guardian Defender.png"])
c.true("...and hid the character entirely", "Farseer.png" not in pre_order[:2])

# A unit with no attached character is untouched by any of this.
c.eq("a unit with one image has one thumbnail",
     base(sprites.portrait_paths(
         tk.build(STRIKING_SCORPIONS, "Player 1", name="Striking Scorpions 1"), 4)),
     ["Striking Scorpion.png"])
c.eq("no squad, no art", sprites.portrait_paths(None), [])


# ---------------------------------------------------------------------------
# 2. every roll of an attack sequence carries both units
# ---------------------------------------------------------------------------

print("--- 2. rolls carry the matchup ---")


def drive(scene, controller, kick):
    """Runs one whole activation, recording (label, attacker, target) for
    every roll it puts on the dice manager."""
    seen = []
    dice = scene["dice"]

    def note():
        if dice.is_pending:
            seen.append((dice.label, dice.attacker_squad, dice.target_squad))

    kick()
    note()
    for _ in range(200):
        if dice.is_pending:
            dice.acknowledge()
            controller.on_dice_acknowledged()
            note()
        elif getattr(controller, "pending_damage_choice", None):
            controller.choose_damage_model(controller.pending_damage_choice[0])
            note()
        elif scene["decision"].is_pending:
            scene["decision"].choose(len(scene["decision"].options) - 1)  # decline
            note()
        else:
            break
    return seen


# 5 on every die: a Boy's Slugga is BS5+, so anything lower stops the
# sequence at the hit roll and there is no Wound/Save step left to check.
tk.script(default=5)
shoot = tk.shooting_scene(BOYZ, GRETCHIN, attacker_owner="Player 2", gap=6.0)
sc = shoot["shooting"]


def kick_shooting():
    from game import shooting as shooting_mod
    sc.start_shooting(shoot["attacker"])
    if sc.state == shooting_mod.CHOOSING_SHOOTING_TYPE:
        sc.choose_shooting_type(sc.available_types[0])
    sc.choose_target_squad(shoot["target"])
    sc.choose_weapon(sc.weapon_eligibility()[0][0])


rolls = drive(shoot, sc, kick_shooting)
c.true("the shooting activation actually rolled something", len(rolls) >= 2)
c.true("every shooting roll names the attacker",
       all(a is shoot["attacker"] for _label, a, _t in rolls))
c.true("every shooting roll names the target",
       all(t is shoot["target"] for _label, _a, t in rolls))
c.true("...including the Save roll, which the DEFENDER throws",
       any("Save Roll" in (label or "") for label, _a, _t in rolls))

tk.script(default=5)
melee = tk.fight_scene(BOYZ, GRETCHIN, attacker_owner="Player 2")
fc = melee["fight"]


def kick_fight():
    fc.select_to_fight(melee["attacker"])
    if fc.target_squad is None:
        fc.choose_target_squad(melee["target"])
    if fc.current_group is None:
        fc.choose_weapon(fc.weapon_eligibility()[0][0])


melee_rolls = drive(melee, fc, kick_fight)
c.true("the fight activation actually rolled something", len(melee_rolls) >= 2)
c.true("every fight roll names the attacker",
       all(a is melee["attacker"] for _label, a, _t in melee_rolls))
c.true("every fight roll names the target",
       all(t is melee["target"] for _label, _a, t in melee_rolls))

# A roll that is nobody's attack must NOT inherit the last one's matchup -
# the fields are per-roll for exactly this reason.
loose = DiceManager()
loose.roll(count=1, sides=6, label="Advance", target_name="2 Boyz 1",
           attacker_squad=shoot["attacker"], target_squad=shoot["target"])
loose.roll(count=2, sides=6, label="Charge Roll", target_name="2 Boyz 1")
c.eq("a later roll clears the attacker", loose.attacker_squad, None)
c.eq("...and the target", loose.target_squad, None)


# ---------------------------------------------------------------------------
# 3. the panel draws it, and stays inside its own width
# ---------------------------------------------------------------------------

print("--- 3. the panel draws it ---")

screen = pygame.display.get_surface()
mob = attached_units.attach(tk.build(WARBOSS, "Player 2", name="Warboss"),
                            tk.build(BOYZ, "Player 2", name="Boyz 1"))


def render(attacker, target, board_w=960, kind=HIT_ROLL, subject_label="Target"):
    """Draws one roll's panel and returns [(art surfaces, name lines, rects)]
    per side, plus the panel's own left edge and width - the panel defers its
    drawing into closures, so the rects are what says where things landed."""
    dice = DiceManager()
    dice.roll(count=4, sides=6, label="Hit Roll: Slugga (4 attack(s))",
              success_threshold=4,
              target_name=target.name if target is not None else None,
              roll_kind=kind, attacker_squad=attacker, target_squad=target,
              subject_label=subject_label)
    panel = DicePanel()
    bounds = pygame.Rect(0, 0, board_w, 700)
    captured = []
    real = DicePanel._draw_unit_side

    def spy(self, ops, movable, surf, arts, lines, colour, x, y, height):
        before = len(movable)
        real(self, ops, movable, surf, arts, lines, colour, x, y, height)
        captured.append((list(arts), list(lines), list(movable[before:])))

    for _ in range(400):                    # let the slide-in / tumble finish
        screen.fill((25, 28, 32))
        panel.draw(screen, dice, bounds_rect=bounds)
        if panel._phase == dp.SHOWN:
            break
        panel._anim_start = -1e9            # skip the wall-clock wait
        panel._flicker_start = -1e9
    captured.clear()
    DicePanel._draw_unit_side = spy
    screen.fill((25, 28, 32))
    panel.draw(screen, dice, bounds_rect=bounds)
    DicePanel._draw_unit_side = real
    width = min(bounds.width - 2 * dp.BACKDROP_MARGIN, dp.MAX_PANEL_WIDTH)
    return captured, bounds.x + (bounds.width - width) // 2, width


sides, left, width = render(merged, mob)
c.eq("both sides of the matchup are drawn", len(sides), 2)
c.true("the attacker side has art", len(sides[0][0]) >= 1)
c.true("the target side has art", len(sides[1][0]) >= 1)
c.true("the attacker sits in the left half",
       all(r.centerx < left + width // 2 for r in sides[0][2]))
c.true("the target sits in the right half",
       all(r.centerx > left + width // 2 for r in sides[1][2]))
c.eq("the attacker's whole name is on screen, wrapped not cut",
     "".join(sides[0][1]).replace(" ", ""), merged.name.replace(" ", ""))
c.eq("...and the target's", "".join(sides[1][1]).replace(" ", ""),
     mob.name.replace(" ", ""))

# No attacker (a Damage roll resolved from inside DamageAllocationSession, a
# battle-shock test) falls back to the single centred "Target: X" line.
only_target, left2, width2 = render(None, mob, kind=SAVE_ROLL)
c.eq("with no attacker there is one side", len(only_target), 1)
c.true("...and it still says Target:", only_target[0][1][0].startswith("Target:"))
spans = only_target[0][2]
c.true("...centred in the panel",
       abs((min(r.left for r in spans) + max(r.right for r in spans)) // 2
           - (left2 + width2 // 2)) <= 4)

# Width sweep: the name has to wrap inside the panel at every window size.
overflow = []
for board_w in (1400, 960, 700, 560, 460, 380, 300):
    got, l, w = render(merged, mob, board_w=board_w)
    for _arts, _lines, rects in got:
        overflow += [(board_w, r) for r in rects if r.left < l or r.right > l + w]
c.eq("nothing overflows the panel at any width", overflow, [])

narrow, _l, _w = render(merged, mob, board_w=380)
c.true("a very narrow panel gives up thumbnails rather than squeeze the name",
       sum(len(arts) for arts, _lines, _rects in narrow) < 4)
c.true("...and still names both units",
       all(lines for _arts, lines, _rects in narrow))

# A/B: with the matchup neutralised the panel is back to the old single
# "Target: X" text - so the checks above are testing the new line, not
# something that was on screen already.
saved = DicePanel._draw_matchup


def old_style(self, ops, movable_rects, surface, attacker_squad, target_squad,
              target_name, y, max_width, panel_left, panel_width, subject_label="Target"):
    return self._draw_wrapped(ops, movable_rects, surface, f"Target: {target_name}",
                              self.target_font, dp.TARGET_COLOR, y, max_width,
                              panel_left + panel_width // 2)


DicePanel._draw_matchup = old_style
pre, _l, _w = render(merged, mob)
DicePanel._draw_matchup = saved
c.eq("PRE-CHANGE: no unit art on the roll at all", pre, [])
post, _l, _w = render(merged, mob)
c.true("POST-CHANGE: it is there",
       sum(len(arts) for arts, _lines, _rects in post) >= 2)


# ---------------------------------------------------------------------------
# 4. a roll whose named unit is not a target
# ---------------------------------------------------------------------------

print("--- 4. non-target rolls ---")

# User: "wenn charge overlay kommt, also wenn angesagt wird, wer den charge
# roll macht - da will ich auch ein sprite haben." A Charge roll names the
# unit DOING the charging (its targets are not chosen yet - they are filtered
# out of whatever the roll reaches), so it needs its own art and its own word
# for what that unit is.
from game.charge import ChargeController          # noqa: E402
from game.turn import PHASE_CHARGE, TurnTracker   # noqa: E402

charger = attached_units.attach(tk.build(WARBOSS, "Player 2", name="2 Warboss 9"),
                                tk.build(BOYZ, "Player 2", name="2 Boyz 9"))
victim = tk.build(GRETCHIN, "Player 1", name="1 Gretchin 9")
tk.line_up(charger, y=20.0)
tk.line_up(victim, y=26.0)
charge_tokens = list(charger.models) + list(victim.models)

charge_turn = TurnTracker(first_player="Player 2")
while charge_turn.phase != PHASE_CHARGE:
    charge_turn.advance_phase()
charge_dice = DiceManager()
charge_controller = ChargeController(
    dice_manager=charge_dice, turn_tracker=charge_turn, all_tokens=charge_tokens,
)
c.true("the charge is actually declarable, so the roll really happens",
       charge_controller.can_declare_charge(charger))
charge_controller.declare_charge(charger)

c.eq("the roll happened", charge_dice.label, "Charge Roll")
c.true("the charging unit is carried, so the panel has art to show",
       charge_dice.target_squad is charger)
c.eq("...and it is named as the CHARGING unit, not as a target",
     charge_dice.subject_label, "Charging")
c.eq("there is no attacker/target pair here - one unit, one side",
     charge_dice.attacker_squad, None)

# It reaches the screen: one side, with art, under that word.
charge_sides, _left, _width = render(None, charger, subject_label="Charging")
c.eq("one side is drawn", len(charge_sides), 1)
c.true("with the charging unit's art", len(charge_sides[0][0]) >= 1)
c.true("...and its own label, not \"Target:\"",
       charge_sides[0][1][0].startswith("Charging:"))

# A/B: the default is still "Target" for everything that did not ask.
plain = DiceManager()
plain.roll(count=1, sides=6, label="Hit Roll: x", target_name=victim.name, target_squad=victim)
c.eq("a roll that says nothing keeps the old wording", plain.subject_label, "Target")
default_sides, _l, _w = render(None, victim)
c.true("...and prints it", default_sides[0][1][0].startswith("Target:"))

c.finish()
