"""Runtime probe: does the Unit Statistics ledger really fill up in a REAL
battle, and does its button really get drawn?

A suite proves the arithmetic. It cannot prove that main.py feeds the ledger
or draws the button - "built but never FED" has caught this repo out six
times, and a source guard only shows that the call is THERE.

Runs selfplay.py's real main() loop through runpy with spies installed on the
reporting helpers and on the button, and reports:

  * how much of each statistic accumulated, and on how many units;
  * HOW MANY WOUNDS COULD NOT BE ATTRIBUTED - the named gap's real size, which
    is the number that decides whether threading a source through the 20
    ability modules that build a MortalWoundAllocationSession is worth doing;
  * whether the STATS button was drawn, and beside the AI switch.

  python verify_unit_stats.py [map] [frames] [--neutralize]

--neutralize restores the world as it was before this feature - the reporting
helpers do nothing and the button is not drawn - and must report zeroes.
"""

import sys

import pygame

from game import battle_stats
from game.ui import unit_stats_overlay
from game.ui.ai_busy_badge import ai_mode_toggle_rect

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

FRAMES = 3000
for arg in list(sys.argv[1:]):
    if arg.isdigit():
        FRAMES = int(arg)
        sys.argv.remove(arg)

RESULT = {
    "damage_calls": 0, "wounds": 0, "unattributed": 0,
    "prevented_calls": 0, "prevented": 0.0,
    "group_calls": 0, "groups_with_misses": 0,
    "move_calls": 0, "inches": 0.0,
    "button_drawn": 0, "button_rect": None, "ai_rect": None,
    "units_with_kills": 0, "units_with_prevented": 0, "units_with_distance": 0,
    "sampled": False,
}

# ---------------------------------------------------------------- the spies
# Every reporting seam looks the helper up on the MODULE at call time
# (game/damage_resolution.py and the rest do `from game import battle_stats`
# then `battle_stats.report_x(...)`), so rebinding the module attribute here,
# before runpy starts main(), is seen by all of them.

_real_damage = battle_stats.report_damage
_real_prevented = battle_stats.report_prevented
_real_group = battle_stats.report_group
_real_move = battle_stats.report_move


def report_damage(attacker_squad, model, amount):
    RESULT["damage_calls"] += 1
    RESULT["wounds"] += amount
    if attacker_squad is None:
        RESULT["unattributed"] += amount
    if not NEUTRALIZE:
        _real_damage(attacker_squad, model, amount)


def report_prevented(model, amount):
    if amount > 0:
        RESULT["prevented_calls"] += 1
        RESULT["prevented"] += amount
    if not NEUTRALIZE:
        _real_prevented(model, amount)


def report_group(group, weapon):
    if group is not None:
        RESULT["group_calls"] += 1
        if group.get("attacks", 0) > group.get("landed", 0):
            RESULT["groups_with_misses"] += 1
    if not NEUTRALIZE:
        _real_group(group, weapon)


def report_move(squad, move_mode, distance_in):
    if distance_in > 0:
        RESULT["move_calls"] += 1
        RESULT["inches"] += distance_in
    if not NEUTRALIZE:
        _real_move(squad, move_mode, distance_in)


battle_stats.report_damage = report_damage
battle_stats.report_prevented = report_prevented
battle_stats.report_group = report_group
battle_stats.report_move = report_move

_real_button = unit_stats_overlay.draw_button


def draw_button(surface, board_rect, font, ai_toggle_rect, mouse_pos=None):
    if NEUTRALIZE:
        # The pre-fix world: main.py drew no such button.
        return None
    rect = _real_button(surface, board_rect, font, ai_toggle_rect, mouse_pos)
    if rect is not None:
        RESULT["button_drawn"] += 1
        RESULT["button_rect"] = tuple(rect)
        RESULT["ai_rect"] = tuple(ai_toggle_rect) if ai_toggle_rect else None
    # Sampled from INSIDE the frame: after runpy returns, main() is gone and
    # so is the ledger it published (it clears battle_stats.CURRENT on the way
    # out), so a count taken afterwards reads a truthful-looking zero.
    ledger = battle_stats.CURRENT
    if ledger is not None:
        RESULT["sampled"] = True
        RESULT["units_with_kills"] = len(ledger.top_killers("Player 1", limit=99)) \
            + len(ledger.top_killers("Player 2", limit=99))
        RESULT["units_with_prevented"] = len(ledger.top_tanks("Player 1", limit=99)) \
            + len(ledger.top_tanks("Player 2", limit=99))
        RESULT["units_with_distance"] = len(ledger.top_movers("Player 1", limit=99)) \
            + len(ledger.top_movers("Player 2", limit=99))
    return rect


unit_stats_overlay.draw_button = draw_button


# ------------------------------------------------------------------- staging
# ONE fact is staged, and here is why. Over 2500 frames a MockAgent battle
# resolved ZERO attack groups - the documented harness limit - so the killing
# and tanking seams are passively unreachable and a passive counter would
# report a clean zero that reads exactly like a pass. What is staged is an
# ATTACK; everything after it is real: main()'s own squads, a real
# DamageAllocationSession, the real _finish_apply(), the real ledger main()
# published, and the real top_killers() the overlay reads.
def _stage_attack(locals_):
    from game.damage_resolution import DamageAllocationSession
    from game.feel_no_pain import FeelNoPainRoll

    state = locals_.get("state")
    if state is None:
        return
    squads = [s for s in state.all_squads() if s.models]
    attacker = next((s for s in squads if s.owner == "Player 2"), None)
    target = next((s for s in squads if s.owner == "Player 1"), None)
    if attacker is None or target is None:
        return
    weapon = next((w for m in attacker.models for w in m.weapons), None)
    if weapon is None:
        return
    RESULT["staged"] = "%s -> %s" % (attacker.name, target.name)
    # Rolls of 1 always fail their save (rule 05.04), so damage really lands.
    DamageAllocationSession([1, 1], weapon, target, attacker_squad=attacker)
    # ...and a Feel No Pain roll with no dice_manager resolves at once, which
    # is the reduction path record_prevented() sits on.
    FeelNoPainRoll(target.models[0], 2, None)


def _drive_with_staging():
    """selfplay's real main() loop, with one attack staged mid-battle.

    Reaches main()'s live locals through a pygame.display.flip counter, the
    same way verify_save_load.py does - main() is a 4000-line function and its
    state exists nowhere else."""
    real_flip = pygame.display.flip
    count = {"n": 0}
    fired = []

    def flip(*args, **kwargs):
        count["n"] += 1
        if count["n"] == STAGE_AT and not fired:
            fired.append(True)
            frame = sys._getframe(1)
            while frame is not None and frame.f_code.co_name != "main":
                frame = frame.f_back
            if frame is not None:
                try:
                    _stage_attack(frame.f_locals)
                except Exception as exc:            # a probe must not mask a real run
                    RESULT["stage_error"] = repr(exc)
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.display.flip = real_flip
    return bool(fired)


# --------------------------------------------------------------------- drive
RESULT["staged"] = None
RESULT["stage_error"] = None
STAGE_AT = max(50, FRAMES // 2)

sys.argv = ["selfplay.py"] + sys.argv[1:] + [str(FRAMES)]
import runpy
_reached = _drive_with_staging()

# -------------------------------------------------------------------- report
print("\n" + "=" * 70)
print("UNIT STATISTICS%s" % ("  (--neutralize: the pre-fix world)" if NEUTRALIZE else ""))
print("=" * 70)
# WHAT THE SEAMS OFFERED. Counted by the spy, so these keep counting under
# --neutralize too - the point of the run is the block BELOW, which is what
# actually reached the ledger.
print("  seams reached, as offered by the engine:")
print("    attack groups resolved    %d  (of those, %d had attacks that never landed)"
      % (RESULT["group_calls"], RESULT["groups_with_misses"]))
print("    wounds offered            %d in %d allocations"
      % (RESULT["wounds"], RESULT["damage_calls"]))
print("    ...of which UNATTRIBUTED  %d   <- the named gap's real size"
      % RESULT["unattributed"])
print("    damage turned aside       %.0f in %d reductions (Feel No Pain / reduction)"
      % (RESULT["prevented"], RESULT["prevented_calls"]))
print("    distance offered          %.1f inches over %d confirmed moves"
      % (RESULT["inches"], RESULT["move_calls"]))
print()
print("  WHAT REACHED main()'s OWN LEDGER - the resume the overlay would show:")
print("    units on the killing table  %d" % RESULT["units_with_kills"])
print("    units on the tanking table  %d" % RESULT["units_with_prevented"])
print("    units on the fastest table  %d" % RESULT["units_with_distance"])
print()
print("  staged attack               %s" % (RESULT["staged"] or "NONE - main()'s frame was not reached"))
if RESULT["stage_error"]:
    print("     staging error            %s" % RESULT["stage_error"])
print("  STATS button drawn          %d frames" % RESULT["button_drawn"])
print("     at                       %s" % (RESULT["button_rect"],))
print("     AI switch at             %s" % (RESULT["ai_rect"],))

beside = False
if RESULT["button_rect"] and RESULT["ai_rect"]:
    bx, by, bw, bh = RESULT["button_rect"]
    ax, ay, aw, ah = RESULT["ai_rect"]
    beside = (bx + bw <= ax) and by == ay and bh == ah
    print("     beside the AI switch?    %s" % beside)

print("=" * 70)

if NEUTRALIZE:
    ok = (RESULT["button_drawn"] == 0
          and RESULT["units_with_distance"] == 0
          and RESULT["units_with_kills"] == 0)
    print("neutralized: nothing recorded and no button drawn -> %s"
          % ("as expected" if ok else "UNEXPECTED"))
    raise SystemExit(0 if ok else 1)

if not RESULT["sampled"]:
    print("INCONCLUSIVE: the button was never drawn, so nothing was observed at all.")
    raise SystemExit(2)

# Movement happens in every battle; the attack seams may not be reached in a
# MockAgent run within the frame budget (the documented harness limit), so
# they are reported as inconclusive rather than counted as a failure.
ok = (RESULT["button_drawn"] > 0 and beside
      and RESULT["units_with_distance"] > 0        # the movement seam, passively
      and RESULT["units_with_kills"] > 0           # the damage seam, from the staged attack
      and RESULT["prevented"] > 0                  # Feel No Pain, likewise
      and RESULT["stage_error"] is None)
if RESULT["group_calls"] == 0:
    print("NOTE: no attack group resolved on its own in this run - that is the")
    print("      documented MockAgent limit, and the reason one attack is staged.")
    print("      test_battle_stats.py drives whole activations through the real")
    print("      controllers for the arithmetic itself.")
print("verdict: %s" % ("OK" if ok else "FAILED"))
raise SystemExit(0 if ok else 1)
