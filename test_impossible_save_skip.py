"""A Save roll nobody could pass is not rolled at all.

User report: "Save Rolls, die man gar nicht bestehen kann, sollten auch gar
nicht gewuerfelt werden. Manchmal werden da 6en gewuerfelt, die dann aber rot
sind."

Reproduced before any change: a Gauss Destructor (AP-4) against Sv4+ Windriders
with no invulnerable save needs an 8+. Every die in that roll is red before it
leaves the cup, and the dice panel still stops the game to have the defender
acknowledge a decision that does not exist.

THE ONE PIECE OF CARE IN THE WHOLE CHANGE is section 2. The roll sites size
their panel off displayed_save_threshold() for ONE representative model - the
one-representative shortcut CLAUDE.md warns about - but
DamageAllocationSession._advance() re-derives save_thresholds() PER MODEL as it
allocates. So a unit whose bodyguards need an 8+ can still hold a character
with an invulnerable save who does not, and skipping on the representative
would silently delete that model's save. save_is_impossible() therefore asks
EVERY living model, and section 2 measures exactly that case with a real
attached unit rather than asserting it.

Sections:
  1. the predicate, at the 6+/7+ boundary
  2. the mixed unit - one model with an invulnerable save keeps the roll
  3. end to end through the real ShootingController, with the counter-case
  4. the log tells the truth - no dice list for a roll that never happened
  5. source: all four Save-roll sites go through the same gate
"""
import copy
import io

import testkit as tk
from testkit import Checks

from game import attached_units
from game.damage_resolution import (AUTO_FAILED_SAVE, displayed_save_threshold,
                                    save_is_impossible)
from game.factions.aeldari import WARLOCK_SKYRUNNERS, WINDRIDERS
from game.factions.necrons import LOKHUST_HEAVY_DESTROYERS

ck = Checks("impossible saves are not rolled")


def _weapon(squad, needle):
    for model in squad.models:
        for weapon in model.weapons:
            if needle.lower() in weapon.name.lower():
                return weapon
    raise AssertionError("no weapon matching %r" % needle)


def _with_ap(weapon, ap):
    """A copy at a different AP. Copied, never mutated in place - weapon
    instances are per model and an edit here would leak (CLAUDE.md)."""
    other = copy.copy(weapon)
    other.ap = ap
    return other


def _scene(target_sheet=WINDRIDERS, gap=6.0):
    return tk.shooting_scene(LOKHUST_HEAVY_DESTROYERS, target_sheet, gap=gap)


# ============================================ 1. the predicate at its boundary
print("\n=== 1. the predicate ===")

sc = _scene()
target, model = sc["target"], sc["target"].models[0]
gauss = _weapon(sc["attacker"], "Gauss Destructor")

ck.eq("the reported case: Sv4+ under AP-4 needs an 8+",
      displayed_save_threshold(model, gauss), 8)
ck.true("...so no die can pass it and the roll is skippable",
        save_is_impossible(target, gauss))

ck.eq("the same gun at AP0 leaves the printed 4+",
      displayed_save_threshold(model, _with_ap(gauss, 0)), 4)
ck.true("...and that roll is still made",
        not save_is_impossible(target, _with_ap(gauss, 0)))

# The boundary from BOTH sides. A test that only compared 4+ against 8+ would
# pass just as happily with the comparison written `>= 6` as with `> 6`.
ck.eq("AP-2 makes it exactly a 6+", displayed_save_threshold(model, _with_ap(gauss, -2)), 6)
ck.true("a save needing exactly 6+ is NOT skipped",
        not save_is_impossible(target, _with_ap(gauss, -2)))
ck.eq("AP-3 makes it a 7+", displayed_save_threshold(model, _with_ap(gauss, -3)), 7)
ck.true("a save needing 7+ IS skipped", save_is_impossible(target, _with_ap(gauss, -3)))

# A wiped-out unit has nothing to allocate to; the caller's own wounds<=0 guard
# and DamageAllocationSession's "wasted" path own that case, not this one.
_dead = _scene()["target"]
for _m in _dead.models:
    _m.current_wounds = 0
ck.true("an emptied unit is not reported as unsaveable",
        not save_is_impossible(_dead, gauss))


# ============================== 2. the mixed unit - the one that must NOT skip
print("\n=== 2. a mixed unit keeps its roll ===")

# Windriders (Sv4+, no invulnerable) led by a Warlock Skyrunner (Sv6+, Inv4+).
# Under AP-4 the bodyguards need an 8+ and the character still saves on a 4+.
mixed = _scene()
attached_units.attach(
    tk.build(WARLOCK_SKYRUNNERS, mixed["target"].owner, name="Warlock Skyrunners"),
    mixed["target"])
mixed_target = mixed["target"]
gauss2 = _weapon(mixed["attacker"], "Gauss Destructor")

thresholds = sorted({displayed_save_threshold(m, gauss2) for m in mixed_target.models})
ck.true("the unit really is mixed - bodyguards at 8+, the character at 4+ %s"
        % thresholds, 8 in thresholds and 4 in thresholds)
ck.true("the REPRESENTATIVE model alone would say 'impossible'",
        displayed_save_threshold(mixed_target.models[0], gauss2) > 6)
ck.true("...but the UNIT does not, because one model can still save",
        not save_is_impossible(mixed_target, gauss2))


# ================================ 3. end to end through the real controller
print("\n=== 3. end to end ===")


def _run(scene, faces=4):
    """Drive one full activation; every die comes up `faces`."""
    tk.script(default=faces)
    shooting, dice = scene["shooting"], scene["dice"]
    shooting.start_shooting(scene["attacker"])
    if shooting.state == "choosing_shooting_type":
        shooting.choose_shooting_type(shooting.available_types[0])
    shooting.choose_target_squad(scene["target"])
    if shooting.state == "choosing_weapon":
        shooting.choose_weapon(shooting.remaining_weapon_types[0])
    for _ in range(120):
        if dice.is_pending:
            dice.acknowledge()
            shooting.on_dice_acknowledged()
        elif shooting.pending_damage_choice:
            shooting.choose_damage_model(shooting.pending_damage_choice[0])
        else:
            break
    return scene


def _save_rolls(scene):
    return [v for label, v in scene["dice"].rolled if "Save Roll" in label]


def _alive(squad):
    return sum(1 for m in squad.models if not m.is_dead())


# Every die a 4: hits, wounds, and - the point - a save that WOULD pass a 4+.
# If the roll happened and were resolved off the printed armour save, this
# wound would be stopped. It must not be.
run = _run(_scene())
ck.eq("no Save roll is thrown at all", len(_save_rolls(run)), 0)
ck.true("the hit and wound rolls still are",
        any("Hit Roll" in l for l, _ in run["dice"].rolled)
        and any("Wound Roll" in l for l, _ in run["dice"].rolled))
ck.eq("the wound still lands - a model is destroyed", _alive(run["target"]), 2)

# THE COUNTER-CASE, same gun, same harness, only the target changed: Warlock
# Skyrunners save on their 4+ invulnerable against AP-4, so the roll happens
# and the 4 saves. Without this the section would also pass if the fix had
# removed every save roll in the game.
kept = _run(_scene(target_sheet=WARLOCK_SKYRUNNERS))
ck.eq("a target that CAN save still gets its roll", len(_save_rolls(kept)), 1)
ck.eq("...and passes it - nothing is destroyed",
      _alive(kept["target"]), len(kept["target"].models))


# =================================================== 4. the log tells the truth
print("\n=== 4. the log ===")

lines = run["log"].lines
summary = next((l for l in lines if "save roll" in l.lower()), "")
ck.true("a summary line is still written: %r" % summary, bool(summary))
ck.true("...and it says the roll was not made, with the number: %r" % summary,
        "not rolled" in summary and "8+" in summary)
ck.true("...and it lists NO dice, because none were thrown: %r" % summary,
        "[" not in summary)
ck.true("the reason is spelled out on its own line too",
        any("no save is possible" in l and "go straight through" in l for l in lines))
ck.true("the kept roll DOES list its dice, so the two read differently",
        any("save roll [" in l.lower() for l in kept["log"].lines))

ck.eq("the stand-in face is rule 05.04's always-failing 1", AUTO_FAILED_SAVE, 1)


# ========================================================= 5. the source gate
print("\n=== 5. every Save-roll site goes through the gate ===")

for name in ("game/shooting.py", "game/fight.py"):
    src = io.open(name, encoding="utf-8").read()
    sites = src.count("roll_kind=SAVE_ROLL")
    gates = src.count("self._skip_impossible_save(")
    ck.true("%s: every SAVE_ROLL site is preceded by the gate (%d sites, %d gates)"
            % (name, sites, gates), sites == gates and sites >= 2)
    ck.true("%s: skipped and acknowledged paths share ONE continuation" % name,
            src.count("def _continue_after_save(") == 1
            and src.count("self._continue_after_save(") >= 4)
    # [PRECISION] is a choice about WHERE the wounds land, independent of
    # whether a die could have stopped them - it must survive the skip.
    ck.true("%s: [PRECISION] is still offered on the skipped path" % name,
            "_precision_choice_needed" in src.split("def _continue_after_save(")[1][:900])

ck.finish()
