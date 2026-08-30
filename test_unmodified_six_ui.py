"""Aspect Shrine / Branching Fates are spent from the LEFT PANEL now, not
answered in an overlay after every roll.

User: "momentan werde ich bei aeldari jedes mal gefragt, ob ich aspect shrine
tokens verwenden will, um wuerfel ergebnisse zu manipulieren. nach jedem wurf.
kann das nicht eine option im linken panel sein, statt eines overlays? command
reroll funktioniert ja auch so. ich klicke aspect shrine button an und waehle
dann den wuerfel aus, den ich aendern will. genau das gleiche mit branching
fates vom farseer."

Measured before changing anything: the prompt was raised in the exact frame
the player acknowledged the roll (dice pending -> acknowledge -> decision
pending, in one step), so every roll cost two clicks.

test_aspect_shrine.py and test_farseer.py cover the abilities themselves. This
covers what they cannot see:
  1. the CONTROLLER's flow, including the states that must not offer;
  2. the PANEL, through the real ActionPanel - a button nobody draws is not a
     button;
  3. the WIRING in main.py, which is where this repo has lost an input five
     times over (error class 15) and shipped an unfed controller three times.
"""
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import script
from game import aspect_shrine, branching_fates, config, unmodified_six
from game.dice import DAMAGE_ROLL, HIT_ROLL, WOUND_ROLL, CHARGE_ROLL
from game.factions import aeldari as ae
from game.unmodified_six_controller import ROLL_KINDS, SOURCES, UnmodifiedSixController
from game.ui.action_panel import ActionPanel

c = tk.Checks("unmodified-6 abilities in the left panel")


def section(title):
    print(f"\n--- {title} ---")


pygame.init()
pygame.display.set_mode((1200, 800))

# 19 hits and one miss on a 3+ - the miss is what a token buys.
HIT_FACES = [4] * 19 + [1]


def scene(faces=HIT_FACES, gap=14.0):
    """A Dire Avengers group mid-activation, stopped at the pending Hit roll."""
    sc = tk.shooting_scene(ae.DIRE_AVENGERS, ae.HOWLING_BANSHEES,
                           attacker_owner="Player 1", gap=gap)
    sc["shooting"].start_shooting(sc["attacker"])
    sc["shooting"].choose_target_squad(sc["target"])
    key = next(r[0] for r in sc["shooting"].weapon_eligibility()
               if r[1] == "Avenger Shuriken Catapult")
    script(*faces)
    sc["shooting"].choose_weapon(key)
    sc["ctrl"] = UnmodifiedSixController(
        sc["dice"], attack_controllers=(sc["shooting"],), game_log=sc["log"])
    return sc


# ------------------------------------------------------- 1. the flow

section("1. the controller's flow")

sc = scene()
ctrl = sc["ctrl"]
c.true("the roll really is pending", sc["dice"].is_pending)
c.eq("...and it is a Hit roll", sc["dice"].roll_kind, HIT_ROLL)
c.eq("no overlay is raised - the whole point", sc["decision"].is_pending, False)
c.true("the button is offered", ctrl.can_use(aspect_shrine))

# Nothing happens until a die is picked: the button opens a selection, it does
# not spend.
ctrl.start(aspect_shrine)
c.true("clicking it opens die selection", ctrl.selecting_die)
c.eq("...spending nothing yet", aspect_shrine.unspent_tokens(sc["attacker"]), 1)
c.eq("...and changing no die", sorted(set(sc["dice"].pending_values)), [1, 4])

# A click on a die that is already a 6 is ignored rather than spending on
# nothing - the same shape as CommandRerollController.choose_die(). Needs a
# roll with SEVERAL changeable dice, or start() takes the single-candidate
# shortcut below and there is no selection to click into.
sixes = scene([6] * 10 + [4] * 9 + [1])
sixes["ctrl"].start(aspect_shrine)
c.true("this roll really does open a selection", sixes["ctrl"].selecting_die)
six_index = next(i for i, v in enumerate(sixes["dice"].pending_values) if v == 6)
sixes["ctrl"].choose_die(six_index)
c.true("clicking a die that is already a 6 is ignored", sixes["ctrl"].selecting_die)
c.eq("...and costs nothing", aspect_shrine.unspent_tokens(sixes["attacker"]), 1)
c.eq("...and the die is untouched", sixes["dice"].pending_values[six_index], 6)

# Cancel puts it back with nothing spent.
ctrl.cancel_selection()
c.eq("cancel closes the selection", ctrl.selecting_die, False)
c.eq("...and spends nothing", aspect_shrine.unspent_tokens(sc["attacker"]), 1)
c.true("...and the button is still there", ctrl.can_use(aspect_shrine))

# The single-candidate shortcut: with one changeable die there is nothing to
# choose, so it applies straight away (Command Re-roll does the same).
one = scene([6] * 19 + [1])
one.setdefault("x", None)
c.eq("only one die is changeable", len(one["ctrl"]._changeable_indices()), 1)
one["ctrl"].start(aspect_shrine)
c.eq("...so no selection step opens", one["ctrl"].selecting_die, False)
c.eq("...and it is already applied", aspect_shrine.unspent_tokens(one["attacker"]), 0)
c.eq("...on the one die that could change", one["dice"].pending_values[-1], 6)

# States that must NOT offer.
no_resource = scene()
no_resource["attacker"].aspect_shrine_tokens = 0
c.eq("no token, no button", no_resource["ctrl"].available_sources(), [])

wrong_kind = scene()
wrong_kind["dice"].roll_kind = CHARGE_ROLL
c.eq("a Charge roll is not one of these rolls", wrong_kind["ctrl"].available_sources(), [])

no_context = scene()
no_context["shooting"].current_group = None
c.eq("no weapon group open, no button", no_context["ctrl"].available_sources(), [])

acknowledged = scene()
acknowledged["dice"].acknowledge()
c.eq("nothing on the table, nothing to offer", acknowledged["ctrl"].available_sources(), [])

# reset() clears a selection whose roll has gone - otherwise the panel would
# sit in a mode with nothing left to click.
stranded = scene()
stranded["ctrl"].start(aspect_shrine)
c.true("selection open", stranded["ctrl"].selecting_die)
stranded["ctrl"].reset()
c.eq("reset() closes it", stranded["ctrl"].selecting_die, False)

# Both abilities go through ONE controller, so a unit holding both must get
# both buttons - the case a per-ability controller would have got wrong.
#
# No such unit exists in this engine, and that is a fact worth pinning rather
# than working around: the Farseer's LEADER line names only Guardian Defenders
# and Storm Guardians, and neither carries an Aspect Shrine. So the resource
# lookup is stubbed for this one check - the thing under test is the
# CONTROLLER's handling of two live sources, not whether the rules allow it.
c.true("the Farseer cannot in fact lead an Aspect Warrior unit",
       "Dire Avengers" not in " ".join(getattr(ae.FARSEER, "leads", ()) or ()))

both = scene()
_real_available = branching_fates.available
branching_fates.available = lambda squad: True
try:
    offered = [s.__name__ for s, _sq, _m in both["ctrl"].available_sources()]
    c.eq("a unit with both abilities is offered both", offered,
         ["game.aspect_shrine", "game.branching_fates"])
    c.eq("...in the order SOURCES declares", offered, [s.__name__ for s in SOURCES])
    # Spending one must leave the other - two resources, not one.
    both["ctrl"].start(aspect_shrine)
    both["ctrl"].choose_die(next(i for i, v in enumerate(both["dice"].pending_values) if v == 1))
    c.eq("the token is spent", aspect_shrine.unspent_tokens(both["attacker"]), 0)
    c.eq("...and Branching Fates is untouched",
         getattr(both["attacker"], "branching_fates_used", False), False)
finally:
    branching_fates.available = _real_available


# The DAMAGE roll is Branching Fates' third roll type, and it goes down its own
# path: one die, no selection step, and the die is set to whatever face makes
# the RESULT 6 (a D6+2 needs a 4). test_farseer.py drives it end to end; here
# only the two things this controller decides.
c.eq("Aspect Shrine does not cover Damage rolls",
     DAMAGE_ROLL in ROLL_KINDS[aspect_shrine], False)
c.true("Branching Fates does", DAMAGE_ROLL in ROLL_KINDS[branching_fates])
# The wiring guard below checks the hook exists on both attack controllers.


# ------------------------------------------------------- 2. the panel

section("2. the real ActionPanel")

panel = ActionPanel()
surface = pygame.display.get_surface()
rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 700)


def panel_buttons(sc, ctrl=None):
    surface.fill((0, 0, 0))
    panel.draw(surface, rect, sc["shooting"].movement_controller if hasattr(sc["shooting"], "movement_controller")
               else sc["move"], sc["shooting"],
               dice_manager=sc["dice"], unmodified_six_controller=ctrl or sc["ctrl"])
    return [b[0] for b in panel._buttons]


# The panel needs a movement controller; shooting_scene does not build one.
from game.movement import MovementController  # noqa: E402


def with_panel(sc):
    sc["move"] = MovementController(turn_tracker=sc["turn"], all_tokens=sc["state"].tokens,
                                    dice_manager=sc["dice"], obstacles=[])
    return sc


_labels = []
_real_button = ActionPanel._draw_button


def _spy_button(self, surface, rect_, label, **kwargs):
    _labels.append(label)
    return _real_button(self, surface, rect_, label, **kwargs)


ActionPanel._draw_button = _spy_button


def draw_labels(sc):
    _labels.clear()
    surface.fill((0, 0, 0))
    panel.draw(surface, rect, sc["move"], sc["shooting"],
               dice_manager=sc["dice"], unmodified_six_controller=sc["ctrl"])
    return list(_labels)


sc = with_panel(scene())
labels = draw_labels(sc)
c.true("the panel draws an Aspect Shrine button",
       any("Aspect Shrine" in l for l in labels))
c.true("...and it says how many tokens are left", any("1 token" in l for l in labels))

# Once selection is open the panel switches to "pick a die", and offers a way
# out - the same screen Command Re-roll's own selection shows.
sc["ctrl"].start(aspect_shrine)
labels = draw_labels(sc)
# "Only a Cancel" among the SCREEN's own buttons - _draw_global_toolbar()
# always adds its two toggles afterwards, by design (they are global).
c.true("while selecting, a Cancel is offered", "Cancel" in labels)
c.eq("...and the ability button is gone while picking",
     [l for l in labels if "Aspect Shrine" in l], [])
sc["ctrl"].cancel_selection()

# Nothing to offer -> no button, and specifically no empty one.
sc["attacker"].aspect_shrine_tokens = 0
labels = draw_labels(sc)
c.eq("no token, no button", [l for l in labels if "Aspect Shrine" in l], [])

# The colour is its own - it must not read as the pile-in warning next to it.
from game.ui import action_panel as ap  # noqa: E402
c.true("the accent is distinct from the others",
       ap.UNMODIFIED_SIX_ACCENT_COLOR not in (ap.ERROR_COLOR, ap.PILE_IN_ACCENT_COLOR,
                                              ap.DAMAGE_CHOICE_ACCENT_COLOR,
                                              ap.COHERENCY_ACCENT_COLOR))

ActionPanel._draw_button = _real_button


# ------------------------------------------------------- 3. the wiring

section("3. main.py wiring")

src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"),
              encoding="utf-8").read()
lines = src.split("\n")


def line_of(needle):
    return next((i for i, l in enumerate(lines) if needle in l), None)


c.eq("the controller is built exactly once", src.count("UnmodifiedSixController("), 1)
c.eq("...and imported", src.count("from game.unmodified_six_controller import"), 1)

# It reads both attack controllers, so it must be built after both exist.
built = line_of("unmodified_six_controller = UnmodifiedSixController(")
c.true("built after ShootingController", line_of("shooting_controller = ShootingController(") < built)
c.true("built after FightController", line_of("fight_controller = FightController(") < built)

# The panel gets it, or no button is ever drawn.
c.eq("the panel is given the controller",
     src.count("unmodified_six_controller=unmodified_six_controller"), 1)

# The die click is routed. Without this the button opens a selection that
# nothing can answer - exactly the "built but never fed" shape this repo has
# shipped three times.
c.eq("a die click reaches choose_die()", src.count("unmodified_six_controller.choose_die("), 1)
click_i = line_of("unmodified_six_controller.choose_die(")
reroll_i = line_of("command_reroll_controller.choose_die(")
c.true("...inside the same pending-dice branch as Command Re-roll's",
       click_i is not None and reroll_i is not None and abs(click_i - reroll_i) < 30)

# A selection must not outlive the roll it belonged to.
reset_i = line_of("unmodified_six_controller.reset()")
ack_i = line_of("                        dice_manager.acknowledge()")
move_i = line_of("movement_controller.on_dice_acknowledged()")
c.true("reset() runs on the acknowledge path", reset_i is not None and ack_i is not None)
# Guarded rather than compared straight: with reset() removed this used to
# raise on None instead of failing, and a probe that crashes the suite tells
# you less than one that names the missing line.
c.true("...right after the acknowledge, before the controllers are told",
       None not in (reset_i, ack_i, move_i) and ack_i < reset_i < move_i)

# The dice panel highlights dice while ANY of the die-selection modes is open.
# There were two when this was written; the gunships' Targeting Array made it
# three, and this line went red rather than passing unnoticed - which is what
# it was for. Each mode is asserted separately so a fourth one added without
# reaching the panel is caught the same way.
_selecting = src.split("selecting_die=", 1)[1].split("\n\n", 1)[0]
for _mode in ("command_reroll_controller.selecting_die",
              "unmodified_six_controller.selecting_die",
              "targeting_array_controller.selecting_die"):
    c.true(f"the dice panel knows about {_mode.split('_controller')[0]}'s selection",
           _mode in _selecting)

# And the old prompt path is really gone from both attack controllers.
for path in ("game/shooting.py", "game/fight.py"):
    attack_src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), path),
                         encoding="utf-8").read()
    c.eq(f"{path}: no aspect-shrine prompt left", attack_src.count("_offer_aspect_shrine"), 0)
    c.true(f"{path}: provides the context hook",
           "def unmodified_six_context(self):" in attack_src)
    c.true(f"{path}: and it hands over the ADJUSTED weapon",
           "self._adjusted_weapon(pairs, target_squad)" in attack_src)
    # The Damage hook, on BOTH - the prompt it replaces was only ever built by
    # shooting.py, so Branching Fates' Damage half never worked in melee at
    # all. Going through the dice manager fixes that for free.
    c.true(f"{path}: provides the DAMAGE context hook",
           "def unmodified_six_damage_context(self):" in attack_src)

# And the old Damage prompt is gone from the session and the ability module.
dmg_src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "game", "damage_resolution.py"), encoding="utf-8").read()
c.eq("DamageAllocationSession has no damage_override seam left",
     dmg_src.count("damage_override"), 0)
bf_src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "game", "branching_fates.py"), encoding="utf-8").read()
c.eq("...and the prompt class is gone", bf_src.count("BranchingFatesDamageOffer"), 0)
c.true("...while damage_change() - the rule reading - stays",
       "def damage_change(" in bf_src)

c.finish()
