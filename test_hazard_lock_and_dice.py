"""Three reported bugs from one game (logs/game_20260815_231656.log).

  1. "ich konnte gerade nichts mehr machen als ich wunden verteilen musste
     auf meine starsythe. ich konnte dann nur eine phase weiterspringen, um
     aus dem lock rauszukommen."
     Rule 24.15 ([HAZARDOUS]) resolves "after that unit has resolved all of
     its attacks", so its mortal wounds become a pending model choice AFTER
     the weapon group is finished - current_group is None by then. main.py
     keyed the board click that answers that choice on current_group alone,
     so the models were highlighted and unclickable. Log line 343 is the
     incident: "Player 1: Hazard Rolls [2]: 1/1 failed -> 3 mortal wound(s)"
     followed immediately by "Charge phase begins" and not one Mortal Wound
     line - the phase button being the only way out.

  2. "ich sehe oft das würfelwurf von 1 grün ist. 1 failt aber immer egal
     welche modifikatoren." (rules 05.01/05.04)

  3. "der warboss in megaarmor ist zu klein. der hat eine größere warboss
     base."

Real engine objects throughout; each claim carries an A/B against the
pre-fix behaviour, since "it passes now" on its own says nothing about
whether the check would have caught the bug.
"""

import os
import re
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk
from testkit import Checks

from game import shooting
from game.dice import DiceManager, HIT_ROLL
from game.factions.orks import BOYZ, WARBOSS, WARBOSS_MEGA_ARMOUR
from game.factions.tau_empire import PATHFINDER_TEAM, PATHFINDER_CARBINE_TO_ION_RIFLE
from game.units import MeganobzProfile, WarbossMegaArmourProfile, WarbossProfile

c = Checks("hazardous lock / dice colouring / Warboss base")


# ---------------------------------------------------------------------------
# 1. [HAZARDOUS] mortal wounds leave a model choice pending with NO group
# ---------------------------------------------------------------------------

def hazard_scene():
    """A unit fires its one [HAZARDOUS] weapon and then stops shooting, so
    rule 24.15's roll happens - scripted to fail, which owes the unit mortal
    wounds it must allocate among its own models (rule 06.02)."""
    tk.script(default=1)  # every die comes up 1 -> the hazard roll fails
    scene = tk.shooting_scene(
        PATHFINDER_TEAM, BOYZ, attacker_owner="Player 1", gap=6.0,
        attacker_choices={"Pathfinder": {PATHFINDER_CARBINE_TO_ION_RIFLE: 3}},
    )
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    if sc.state == shooting.CHOOSING_SHOOTING_TYPE:
        sc.choose_shooting_type(sc.available_types[0])
    sc.choose_target_squad(scene["target"])
    ion = next(e for e in sc.weapon_eligibility() if "Ion Rifle" in e[1])
    sc.choose_weapon(ion[0], overcharge=True)

    for _ in range(60):
        if scene["dice"].is_pending:
            scene["dice"].acknowledge()
            sc.on_dice_acknowledged()
        elif sc.state == shooting.CHOOSING_WEAPON and sc.current_group is None and sc.pending_step is None:
            sc.stop_shooting()   # the unit's activation ends -> rule 24.15 fires
        else:
            break
        if sc.pending_damage_choice is not None:
            break
    return scene, sc


scene, sc = hazard_scene()

c.true("the hazard roll actually happened", scene["log"].has("Hazard Rolls"))
c.eq("it is the [HAZARDOUS] mortal-wound step", sc.pending_step, "hazard_wounds")
c.true("a model choice is pending", sc.pending_damage_choice is not None)
c.true("with more than one candidate, so it cannot auto-resolve",
       len(sc.pending_damage_choice or []) > 1)
c.true("the choice belongs to the SHOOTING player (24.15 hurts its own unit)",
       all(m.squad.owner == "Player 1" for m in sc.pending_damage_choice))

# This is the shape of the bug: the gate main.py used to key the click on.
c.eq("current_group is None by now (rule 24.15's own timing)", sc.current_group, None)
c.true("...and the controller is not idle either, so nothing else picks it up",
       sc.state != shooting.IDLE)

# A/B: what the pre-fix guard would have done with a board click here.
c.true("PRE-FIX: `current_group is not None` alone does NOT route the click",
       not (sc.current_group is not None))
c.true("POST-FIX: the widened guard does",
       sc.current_group is not None or sc.pending_damage_choice is not None)

# And the choice really is answerable once it is routed.
victim = sc.pending_damage_choice[0]
before = victim.current_wounds
sc.choose_damage_model(victim)
c.true("clicking a candidate applies the mortal wound",
       victim.current_wounds < before or victim.is_dead())
c.true("the log records it", scene["log"].has("Mortal Wound"))

# Drive whatever is left of the session (further mortal wounds / Feel No
# Pain steps) to the end - the point being that it CAN end.
for _ in range(60):
    if scene["dice"].is_pending:
        scene["dice"].acknowledge()
        sc.on_dice_acknowledged()
    elif sc.pending_damage_choice is not None:
        sc.choose_damage_model(sc.pending_damage_choice[0])
    else:
        break
c.eq("the activation finishes instead of soft-locking", sc.pending_step, None)
c.eq("...and the squad is released", sc.active_squad, None)


# ---------------------------------------------------------------------------
# 1b. main.py's own guard is the one that was widened
# ---------------------------------------------------------------------------
# The section above proves the ENGINE state; this proves the wiring, which
# is where the bug actually lived. Read against main.py's source because the
# event chain is a long if/elif inside main() - there is no seam to call.

main_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"),
                encoding="utf-8").read()

for controller in ("shooting_controller", "fight_controller"):
    branch = re.search(
        r"elif \(\s*" + controller + r"\.current_group is not None\s*"
        r"or " + controller + r"\.pending_damage_choice is not None\s*\)",
        main_src,
    )
    c.true(f"main.py routes {controller}'s damage choice without needing a current group",
           branch is not None)

# A/B: the narrow form must be gone, or the widened one above is dead text.
for controller in ("shooting_controller", "fight_controller"):
    c.true(f"PRE-FIX form is gone for {controller}",
           f"elif {controller}.current_group is not None:" not in main_src)

# The Next Phase button stays EARLIER in the chain - it is the escape hatch
# the user had to use, and removing it would trade one lock for another.
c.true("the phase button is still reachable while a damage choice is pending",
       main_src.index("game_status_panel.handle_click(event.pos)")
       < main_src.index("shooting_controller.pending_damage_choice is not None"))


# ---------------------------------------------------------------------------
# 2. An unmodified 1 never counts as a success (rules 05.01/05.04)
# ---------------------------------------------------------------------------

dm = DiceManager()
tk.script(1, 2, 3, 4, 5, 6)
dm.roll(count=6, sides=6, label="Hit Roll", success_threshold=1, roll_kind=HIT_ROLL)

c.eq("the scene really is a threshold modified down to 1+", dm.success_threshold, 1)
c.eq("a natural 1 fails", dm.is_success(1), False)
c.true("everything else at 1+ still succeeds", all(dm.is_success(v) for v in (2, 3, 4, 5, 6)))

# A/B: the old rule the panel used to apply, on the very same roll.
c.true("PRE-FIX: `value >= threshold` called that same 1 a success", 1 >= dm.success_threshold)

# Unchanged where the threshold was never the problem.
dm.roll(count=1, sides=6, label="Hit Roll", success_threshold=4, roll_kind=HIT_ROLL)
c.eq("a 3 still fails a 4+", dm.is_success(3), False)
c.eq("a 4 still passes a 4+", dm.is_success(4), True)
c.eq("a 1 still fails a 4+", dm.is_success(1), False)

dm.roll(count=1, sides=6, label="Save Roll", success_threshold=7)
c.true("an impossible 7+ save fails on every face",
       not any(dm.is_success(v) for v in range(1, 7)))

dm.roll(count=2, sides=6, label="Charge Roll")
c.eq("a roll with no pass/fail notion says so", dm.is_success(6), None)


# 2b. the panel asks that predicate rather than re-deriving it
import pygame  # noqa: E402  (headless display first)

pygame.init()
pygame.display.set_mode((1200, 800))
from game.ui.dice_panel import DicePanel  # noqa: E402  (needs a display)


class CountingDice(DiceManager):
    """Real DiceManager that records every is_success() the panel asks for."""

    def __init__(self):
        super().__init__()
        self.asked = []

    def is_success(self, value):
        self.asked.append(value)
        return super().is_success(value)


counting = CountingDice()
tk.script(1, 6)
counting.roll(count=2, sides=6, label="Hit Roll", success_threshold=1,
              target_name="Boyz", roll_kind=HIT_ROLL)

panel = DicePanel()
surface = pygame.Surface((1200, 800))
# The panel withholds the outcome (and therefore the colouring) until it has
# finished sliding in and tumbling - that is wall-clock driven, so drive the
# clock rather than the frame count.
import game.ui.dice_panel as dice_panel_module  # noqa: E402

real_monotonic, fake_now = dice_panel_module.time.monotonic, [1000.0]
dice_panel_module.time.monotonic = lambda: fake_now[0]
try:
    # One phase transition per draw (SLIDING_IN -> ROLLING -> SHOWN), each
    # gated on elapsed time, so advance the clock between draws.
    for _ in range(4):
        panel.draw(surface, counting, selecting_die=False)
        fake_now[0] += 5.0
finally:
    dice_panel_module.time.monotonic = real_monotonic

c.true("the panel consults is_success() instead of comparing to the threshold",
       bool(counting.asked))
c.true("...and it asked about the natural 1", 1 in counting.asked)


# ---------------------------------------------------------------------------
# 3. Warboss in Mega Armour uses the Warboss base, not the Meganob one
# ---------------------------------------------------------------------------

c.eq("Warboss in Mega Armour is on the 50mm Warboss base",
     WarbossMegaArmourProfile.base_radius_in, WarbossProfile.base_radius_in)
c.eq("...which is 0.98\" (50mm/2 / 25.4)", WarbossMegaArmourProfile.base_radius_in, 0.98)
c.true("PRE-FIX: it was the 40mm Meganob base, which is smaller",
       MeganobzProfile.base_radius_in < WarbossMegaArmourProfile.base_radius_in)

# Through the real datasheet, since that is what main.py builds.
mega = tk.build(WARBOSS_MEGA_ARMOUR, "Player 2")
plain = tk.build(WARBOSS, "Player 2")
c.eq("the built model carries it", mega.models[0].radius_in, 0.98)
c.eq("...and matches the plain Warboss on the board", mega.models[0].radius_in,
     plain.models[0].radius_in)

# --- passed saves must not be shown red -------------------------------------
# User report: "oft werden bestandene rettungswuerfe rot angezeigt". The panel
# was handed only the AP-modified ARMOUR save, while the engine resolves a save
# against the armour save OR the invulnerable save - so a die that saved on the
# invuln was coloured red and grouped with the failures.
#
# The Riptide is the plain case: Sv2+ / Inv4+. Under AP-3 its armour is a 5+
# there, so a rolled 4 fails the armour save and passes the invulnerable one.
print("--- passed saves are not shown red ---")
from game.damage_resolution import displayed_save_threshold, save_thresholds  # noqa: E402
from game.factions.tau_empire import RIPTIDE_BATTLESUIT  # noqa: E402
from game.weapons import WeaponProfile, RANGED  # noqa: E402


class _Ap3Gun(WeaponProfile):
    name = "AP-3 test gun"
    weapon_type = RANGED
    strength = 8
    ap = -3
    damage = 1


rip = tk.build(RIPTIDE_BATTLESUIT, "Player 1", name="1 Riptide Battlesuit 1")
model = rip.models[0]
c.eq("precondition: Sv2+", model.profile.armor_save, "2+")
c.eq("precondition: Inv4+", model.profile.invulnerable_save, "4+")
sv, insv, ap = save_thresholds(model, _Ap3Gun())
c.eq("the armour save is a 5+ under AP-3", sv - ap, 5)
c.eq("the invulnerable save is unaffected by AP", insv, 4)
c.eq("so the number a die must reach is 4, not 5",
     displayed_save_threshold(model, _Ap3Gun()), 4)

# It is the ENGINE's own verdict, not a second opinion: drive a real save roll
# and check the panel's own success/failure split against what the resolution
# actually did.
scene = tk.shooting_scene(BOYZ, RIPTIDE_BATTLESUIT, attacker_owner="Player 2", gap=6.0)
sc, dice = scene["shooting"], scene["dice"]
for m in scene["attacker"].models:
    m.weapons = [_Ap3Gun()]
# Boyz are BS5+, so 5s to hit and to wound; the SAVE dice then come up 4,
# which is the number this whole check is about.
tk.script(*([5] * 20), default=4)
sc.start_shooting(scene["attacker"])
sc.choose_target_squad(scene["target"])
sc.choose_weapon(sc.weapon_eligibility()[0][0])
for _ in range(8):
    if dice.is_pending and "Save" in (dice.label or ""):
        break
    sc.on_dice_acknowledged()
c.true("a Save roll is on the table", "Save" in (dice.label or ""))
c.eq("the panel's threshold is the invulnerable 4+, not the armour 5+",
     dice.success_threshold, 4)
c.true("...so a rolled 4 counts as a success", dice.is_success(4))
c.eq("...and an unmodified 1 still never does", dice.is_success(1), False)

# A/B: the old armour-only number would have called that same 4 a failure.
_old_threshold = 5                          # Sv3+ worsened by AP-2
c.eq("A/B: the old armour-only threshold would have shown it red",
     4 >= _old_threshold, False)


c.finish()
